import mechanicalsoup
import pytz
import datetime
import argparse
import csv

class NYCCitiBikeParser:
	###
    ### Constants
    ###

    # Time Zone
	nyc_tz = pytz.timezone("America/New_York")

	# urls
	login_url = 'https://member.citibikenyc.com/profile/login'
	login_form_action = 'https://member.citibikenyc.com/profile/login_check'
	login_success_url = 'https://member.citibikenyc.com/profile/'
	trips_page_url = 'https://member.citibikenyc.com/profile/trips/{partner_user_id}?pageNumber={page_index}'

	# classes
	start_date_class = 'ed-table__item__info__sub-info_trip-start-date'
	start_station_class = 'ed-table__item__info__sub-info_trip-start-station'
	end_date_class = 'ed-table__item__info__sub-info_trip-end-date'
	end_station_class = 'ed-table__item__info__sub-info_trip-end-station'
	duration_class = 'ed-table__item__info_trip-duration'
	cost_class = 'ed-table__item__info_trip-cost'

	last_link_class = 'ed-paginated-navigation__pages-group__link_last'
	last_trip_class = 'ed-panel__link_last-trip'

	# Citibike Date Format
	# 08/22/2015 8:52:47AM
	date_format = "%m/%d/%Y %I:%M:%S %p"

	def __init__(self, username, password):
		self.__initialize_browser()
		self.__login(username, password)

	###
	### Public
	###

	def get_trips(self, start_date=None):
		"""
		Returns an array of the logged in users trips
		If start_date is passed, will only return trips after the start_date
		"""
		# Retrieve and parse the trips page
		trips_page_html = self.__get_trips_page_html()
		trips_page = trips_page_html.soup

		# Check the 'last' button to see how many pages of results there are
		final_page_index = int(
		    trips_page.find('a', class_=self.last_link_class).attrs['href'].split('pageNumber=')[1])

		parsed_trips = []

		for page_index in range(final_page_index + 1):
			print("on {0} out of {1}".format(page_index,final_page_index))
			trips_page_html = self.__get_trips_page_html(page_index)
			trips_page = trips_page_html.soup

			trips = trips_page.find('div', class_='ed-table__items')

			for trip in trips:
				# TODO : This is strange, but while adding a test, sometimes trip was a
				# <class 'bs4.element.NavigableString'> instead of a <class 'bs4.element.Tag'>
				# trips is the correct type, so currently checking against its type every time
				if type(trip) != type(trips):
					continue

				parsed_trip = dict()

				# Parse Start Date
				parsed_trip['start_date'] = self.__parse_date(
					trip.find('div', class_=self.start_date_class).text.strip()
				)

				# The trips are in reverse chronological order
				# If the current start date matches the one passed in, stop collecting trips
				if start_date and start_date == parsed_trip['start_date']:
					return parsed_trips

				# Parse End Date
				parsed_trip['end_date'] = self.__parse_date(
					trip.find('div', class_=self.end_date_class).text.strip()
				)

				parsed_trip['start_station'] = trip.find('div', class_=self.start_station_class).text.strip()
				parsed_trip['end_station'] = trip.find('div', class_=self.end_station_class).text.strip()

				# Parse Duration
				parsed_trip['duration'] = self.__parse_duration(
					trip.find('div', class_=self.duration_class).text.strip()
				)

				# Parse Cost
				parsed_trip['cost'] = self.__parse_cost(
					trip.find('div', class_=self.cost_class).text.strip()
				)

				parsed_trips.append(parsed_trip)

		return parsed_trips

	###
    ### Private
    ###

	def __initialize_browser(self):
		browser = mechanicalsoup.Browser()
		self._browser = browser

	def __parse_date(self, date):
		"""
		Accepts a date, and returns a UNIX timestamp (UTC)
		"""
		if date and date != '-':
			naive = datetime.datetime.strptime(date, self.date_format)
			local_dt = self.nyc_tz.localize(naive, is_dst=None)
			timestamp = (local_dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()
			return int(timestamp)
		else:
			return 0

	def __parse_duration(self, duration):
		"""
		Accepts a duration, an returns the duration in seconds
		"""
		if duration and duration != '-':
			minutes, seconds = duration.split(' min ')
			minutes = int(minutes)
			if seconds:
				seconds = int(seconds.rstrip('s'))
			else:
				seconds = 0

			return (minutes * 60) + seconds

		else:
			return 0

	def __parse_cost(self, cost):
		"""
		Accepts a cost string, and returns a float
		"""
		if cost:
			return float(cost[1:])
		else:
			return float(0)

	def __get_trips_page_html(self, page_index=0):
		"""
		Accepts a page index, and returns a page from a users trip history
		"""
		return self._browser.get(self.trips_page_url.format(
			partner_user_id=self._partner_user_id,
			page_index=page_index))

	def __login(self, username, password):
		"""
		Attempts to log in a NYC CitiBike with using username and password
		Throws NYCCitiBikeLoginError on failure
		"""
		login_page = self._browser.get(self.login_url)
		login_form = login_page.soup.select("#loginPopupId")[0].select("form")[0]
		login_form.select("[name=_username]")[0]['value'] = username
		login_form.select("[name=_password]")[0]['value'] = password
		page2 = self._browser.submit(login_form, login_page.url)

		if page2.url != self.login_success_url:
			raise NYCCitiBikeLoginError("Login unsuccessful")

		# parse partner_user_id
		profile_page = page2.soup

		self._partner_user_id = \
			profile_page.find('a', class_=self.last_trip_class).attrs['href'].split('/profile/trips/')[1].split('?')[0]


class NYCCitiBikeLoginError(Exception):
	pass

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Login to Citibike and write trips to csv')
	parser.add_argument("username")
	parser.add_argument("password")
	parser.add_argument("csv_filename")
	args = parser.parse_args()

	parser = NYCCitiBikeParser(args.username, args.password)
	trips = parser.get_trips()
	with open(args.csv_filename, 'w', newline='') as f:
		w = csv.DictWriter(f, trips[0].keys())
		w.writeheader()
		w.writerows(trips)