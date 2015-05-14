function CamerasViewModel() {
    var self = this;

    self.username='user';
    self.password='pass';
    self.cameras=ko.observableArray();

    self.ajax = function(uri, method, data) {
        var request = {
            url: uri,
            type: method,
            contentType: "application/json",
            accepts: "application/json",
            cache: false,
            dataType: 'json',
            data: JSON.stringify(data),
            beforeSend: function(xhr) {
                xhr.setRequestHeader("Authorization","Basic "+btoa(self.username+":"+self.password));},
            error: function(jqXHR) {
                console.log("ajax error "+jqXHR.status);}
        };
        return $.ajax(request)
    }

    self.ajax('/cameras','GET').done(function(data) {
        for (var i = 0; i < data.cameras.length; i++) {
            self.cameras.push(data.cameras[i]);
        }
    });
}

ko.applyBindings(new CamerasViewModel(), $('#main')[0]);
