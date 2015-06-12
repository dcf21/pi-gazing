# Meteor Pi

MeteorPi is a project, run from the [Cambridge Science Centre](http://www.cambridgesciencecentre.org/), producing a network of small, low cost internet enabled observatories and their accompanying software.

## Meteors

As the name suggests, this phase of the project is focused on watching the night skies for meteors (as well as other objects such as the ISS and any passing spy satellites!). Each camera contains a black and white security camera, a Raspberry Pi 2 and some local storage. A full stack from image processing through data storage and exposure through a REST API runs on the Pi, and we've created both a rich web UI and a Python client library to connect to and query the information the system captures. 

## Audience

We're building the MeteorPi cameras to be installed in schools and homes, for those with an interest in astronomy, an interest in learning about data science and those who are just plain curious.

You can follow us on [Twitter @meteorpi](https://twitter.com/meteorpi) and [Facebook meteorpicamera](https://www.facebook.com/meteorpicamera), in the meantime as you're reading this please fork this project and have a play.

## Code

If you think you might want to code something cool with our data you've got two options:

1. You could write some Python code to search the database and do things with the results, we have four Python modules (database, server, model and client), you almost certainly mostly want to look at the client and the model classes it uses - these are defined in the repository at [src/pythonModules](https://github.com/camsci/meteor-pi/tree/master/src/pythonModules) if you want to see the code, or you can read the generated docs at [pythonhosted.org](https://pythonhosted.org/meteorpi_client/index.html). All our modules are uploaded regularly to PyPI, so a simple `pip install meteorpi_client` is enough to get started!
2. You could extend our web interface. The source for this is at [src/cameraWebsite](https://github.com/camsci/meteor-pi/tree/master/src/cameraWebsite), which contains a KnockoutJS based rich client. While we run the website on the same machine as the database and HTTP server this isn't actually required - you could download the web code, make any changes or extensions you fancy, run it locally pointed at the API URL on your camera and everything should work just fine.

There are loads of potential projects, we're working up some as workshops but in the meantime our current list is on the [wiki](https://github.com/camsci/meteor-pi/wiki/Ideas-for-projects) (where there's also other helpful information).
