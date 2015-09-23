var mainApp = angular.module('mainApp', ['ngSanitize','ngCsv']);

mainApp.controller('MainCtrl', ['$scope', '$http', function($scope, $http){
    $scope.username = '';
    $scope.password = '';
    $scope.data_downloaded = false;
    $scope.status = "WAITING";
    $scope.data = null;
    $scope.header = ['w','t','f'];
    $scope.login = function(){
        var data = {'username': $scope.username, 'password': $scope.password};
        $scope.status = "DOWNLOADING....";
        $http.post("/getdata", data).success(function(data){
            $scope.header = Object.keys(data[0]);
            //fake header because it doesnt work
            $scope.data = data;
            $scope.data.unshift($scope.header);
            $scope.data_downloaded = true;
            $scope.status = "DONE!";
        })
    };
}]);
