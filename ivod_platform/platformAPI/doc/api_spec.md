# Endpoints

## chart-add
- url: charts
- Description: List charts or add a new chart
- methods: [GET, POST]
- GET:
    - Returns:
        - Format: JSON
        - Type: [Chart]
        - Code: 200
- POST:
    - Parameters:
        - 'datasource':
            - Description: ID of datasource to be used for this chart
            - Type: int
        - 'chart_name':
            - Description: Name of the chart type to be used, see pive for list of allowed values
            - Type: string
        - 'config':
            - Description: Parameters for chart rendering
            - Type: JSON Object
        - 'scope_path':
            - Description: Object name for displaying/ordering elements in UI
            - Type: string
        - 'downloadable':
            - Description: Determines if the (processed) data can be downloaded
            - Type: boolean
            - Default: False
        - 'visibility':
            - Description: Determines the share level of this chart
            - Type: Enum(Private, Shared, Semi-Public, Public)
            - Default: 0
    - Returns:
        - Format: JSON
        - Type: Chart
        - Code: 201

## chart-get
- url: charts/\<ID\>
- Description: Show, alter or delete a specific chart
- methods: [GET, PATCH, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: Chart
        - Code: 200
- PATCH:
    - Parameters:
        - 'config':
            - Description: Parameters for chart rendering
            - Type: JSON Object
            - Default: Prior Value
        - 'scope_path':
            - Description: Object name for displaying/ordering elements in UI
            - Type: string
            - Default: Prior Value
        - 'downloadable':
            - Description: Determines if the (processed) data can be downloaded
            - Type: boolean
            - Default: Prior Value
        - 'visibility':
            - Description: Determines the share level of this chart
            - Type: Enum(Private, Shared, Semi-Public, Public)
            - Default: Prior Value
    - Returns:
        - Format: JSON
        - Type: Chart
        - Code: 200
- DELETE:
    - Returns:
        - Code: 204
    
## chart-data
- url: charts/\<ID\>/data
- Description: Get processed data for displaying
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: String
        - Code: 200
    
## chart-code
- url: charts/\<ID\>/code
- Description: Redirects to the javascript code associated with this chart. See **code-get**
- methods: [GET]
- GET:
    - Returns:
        - Code: 302
    
## code-get
- url: code/\<version\>/\<name\>
- Description: Returns the javascript to visualise a chart. **chart-code** redirects here.
  Normally this does not need to be called manually
- methods: [GET]
- GET:
    - Returns:
        - Format: Javascript
        - Type: String
        - Code: 200
        
## chart-shared
- url: charts/\<ID\>/shared
- Description: Show, add or remove users this chart is shared with
- methods: [GET, PATCH, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
- PATCH:
    - Parameters:
        - 'users':
            - Description: List of user IDs to add to share
            - Type: [int]
            - Default: []
        - 'groups':
            - Description: List of group IDs to add to share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
- DELETE:
    - Parameters:
        - 'users':
            - Description: List of user IDs to remove from share
            - Type: [int]
            - Default: []
        - 'groups':
            - Description: List of group IDs to remove from share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
        
## datasource-add
- url: datasources
- Description: List datasources or add a new datasource
- methods: [GET, POST]
- GET:
    - Returns:
        - Format: JSON
        - Type: [Datasource]
        - Code: 200
- POST:
    - Parameters:
        - 'scope_path':
            - Description: Object name for displaying/ordering elements in UI
            - Type: string
        - OneOf:
            - 'url':
                - Description: URL that points to the datasource
                - Type: URL
            - 'data':
                - Description: Data to be used as datasource, base64 encoded
                - Type: string
    - Returns:
        - Format: JSON
        - Type: Datasource
        - Code: 201
        
## datasource-get
- url: datasources/\<ID\>
- Description: Show or delete a specific datasource
- methods: [GET, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: Datasource
        - Code: 200
- PATCH:
    - Parameters:
        - 'scope_path':
            - Description: Object name for displaying/ordering elements in UI
            - Type: string
            - Default: Prior Value
    - Returns:
        - Format: JSON
        - Type: Datasource
        - Code: 200
- DELETE:
    - Returns:
        - Code: 204

## datasource-shared
- url: datasources/\<ID\>/shared
- Description: Show, add or remove users this datasource is shared with
- methods: [GET, PATCH, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
- PATCH:
    - Parameters:
        - 'users':
            - Description: List of user IDs to add to share
            - Type: [int]
            - Default: []
        - 'groups':
            - Description: List of group IDs to add to share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
        
- DELETE:
    - Parameters:
        - 'users':
            - Description: List of user IDs to remove from share
            - Type: [int]
            - Default: []
        - 'groups':
            - Description: List of group IDs to remove from share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
    
## datasource-charttypes
- url: datasources/\<ID\>/charttypes
- Description: Show the chart types this datasource can be visualised with
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: [String]
        - Code: 200
        

# Data Types
- Datasource
- Chart
- Shares

## Datasource
- 'id':
    - Description: Database id of datasource
    - Type: int
- 'source':
    - Description: (Original) Source of data
    - Type: URL
- 'scope_path':
    - Description: Object name for displaying/ordering elements in UI
    - Type: string
- 'owner'
    - Description: Database id of owner
    - Type: int

## Chart
- 'id':
    - Description: Database id of chart
    - Type: int
- 'chart_name':
    - Description: Name of the chart type to be used, see pive for list of allowed values
    - Type: string
- 'scope_path':
    - Description: Object name for displaying/ordering elements in UI
    - Type: string
- 'owner'
    - Description: Database id of owner
    - Type: int
- 'original_datasource': 
    - Description: Database id of the datasource the chart is based on, can be null, if datasource has been removed
    - Type: int
- 'config':
    - Description: Parameters for chart rendering
    - Type: JSON Object
- 'downloadable':
    - Description: Determines if the (processed) data can be downloaded
    - Type: boolean
    - Default: False
- 'visibility':
    - Description: Determines the share level of this chart
    - Type: Enum(Private, Shared, Semi-Public, Public)
    - Default: 0

## Shares
- 'users':
    - Description: List of user IDs this share applies to
    - Type: [int]
    - Default: []
- 'groups':
    - Description: List of group IDs this share applies to
    - Type: [int]
    - Default: []