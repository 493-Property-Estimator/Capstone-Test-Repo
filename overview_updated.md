The project base is “Property Value Estimator”, where given a property (this might be given by an address, geo shape, or another means) then calculates what the property is likely worth given a factor of values.

Values to consider for property values:
-	Surrounding property values with proximity
-	Driveability of area
-	Walkability of area
-	Distance to school
-	Distance to store (size of small like convenience, to large like a wholesale or super center)
-	Distance to common work areas (places like downtown are high for common work, where a local strip mall esk area can be medium and a single business is low. This is to get how far a person may have to commute to work)
-	Green spaces of area
-	Crime rates and type of crime
-	etc.


What the estimator needs to be able to do:
-	Because of the data that can be collected, we need the model to be able to accept in some inputs and not have all of them and still be able to output a result. For instance a property in the country might not have any ability to score common work areas as it is all really poor, or crime rates as they might not be available.
-	Be able to calculate its own values when applicable and do this prematurely to reduce response time. Values that line up with this are Walkability and Driveability, it might not give a perfect representation of this but can estimate it.
-	Calculate distances to things from a database for straight line but as well road distance. Schools, green spaces, stores, etc.

What the project needs to pull from:
-	Open data sources such as crime, and map data to then parse through and get the parsed data into a database that can be easier to access
-	Poll open data when it needs to and finding sources for data to constantly add to its own database


What the project might look like:
-	Backend server component that can be polled with by an API
-	Database of collection of features that can be queried
-	Data sourcing program that collects and refinines data and places it into the database and verifies what exists in the database
-	A front end that is user friendly map with input fields for a user
-	A front end control panel to manage the database and data sourcing
-   The user interface should also be smooth and interactive for users to check and uncheck filter criteria and use certain sliders to adjust and fine-tune specific filters.
-   the application should be fast and responsive so the implementation should take into account runtime calculations and consider aggregating data points by taking the mean or median (or both)
-   A final estimated price for a property should be calculated based on all of its surrounding factors added (or subtracted) from its property value tax assessment value (the baseline)
