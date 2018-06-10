# CampStatus: scrape NFS websites for campground statuses

The national forest service has a pretty annoying system
for viewing campground statuses in bulk. CampStatus
interfaces with google sheets and updates campground status.
It is meant to be run as an automated job, either on CRON or some server.

First version of the google sheet is [here](https://docs.google.com/spreadsheets/d/19TrtOtNcBHffXP1NFfz_XB_7xb3LbexpjVSGjyKpHWo/edit?usp=sharing). 
All the columns were manual entry, but one of my goals
is to automate spreadsheet population (though some 
fields might not work out).

Wishlist:
* Scrape NFS sites to populate the google sheet(s)
* Make a web front end other than google sheets
  to tabulate the campground data.

## Dependencies
* numpy
* pandas
* scikit-learn
* geopy
* requests
* BeautifulSoup
* re
* gspread
* oauth2client