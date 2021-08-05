# Endpoints

## chart-add

- url: charts
- Description: List charts or add a new chart
- methods: [GET, POST]
- GET:
    - Parameters:
        - 'chart_type':
            - Type: query
            - Description: Filter for charts with this exact name
        - 'modification_time__lte':
            - Type: query
            - Description: Filter for charts last modified before the passed timestamp argument
        - 'modification_time__gte':
            - Type: query
            - Description: Filter for charts last modified after the passed timestamp argument
        - 'creation_time_lte':
            - Type: query
            - Description: Filter for charts created before the passed timestamp argument
        - 'creation_time__gte':
            - Type: query
            - Description: Filter for charts created after the passed timestamp argument
    - Returns:
        - Format: JSON
        - Type: [Chart]
        - Code: 200
- POST:
    - Parameters:
        - 'datasource':
            - Description: ID of datasource to be used for this chart
            - Type: int
        - 'chart_type':
            - Description: Name of the chart type to be used, see pive for list of allowed values
            - Type: string
        - 'config':
            - Description: Parameters for chart rendering
            - Type: JSON Object
        - 'chart_name':
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
        - 'chart_name':
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

## chart-shared

- url: charts/\<ID\/shared/>
- Description: Show, add, or remove shares from a chart
- methods: [GET, PATCH, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
- PATCH:
    - Parameters:
        - 'users':
            - Description: List of user ids to add to the share
            - Type: [uuid]
            - Default: []
        - 'groups':
            - Description: List of group ids to add to the share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200
- DELETE:
    - Parameters:
        - 'users':
            - Description: List of user ids to remove from the share
            - Type: [uuid]
            - Default: []
        - 'groups':
            - Description: List of group ids to remove from the share
            - Type: [int]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: Shares
        - Code: 200

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

## chart-config

- url: charts/\<ID\>/config
- Description: Get config file for this chart
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: String
        - Code: 200

## chart-files

- url: charts/\<ID\>/files/<filename>
- Description: Get a file associated with this chart.  
  This allows pive visualisations to add more files. Uses a whitelist for filenames.
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: octet-stream
        - Code: 200

## code-common-get

- url: code/\<name\>
- Description: Returns code files common to all charts.
- methods: [GET]
- GET:
    - Returns:
        - Format: Javascript
        - Type: octet-stream
        - Code: 200

## code-get

- url: code/\<version\>/\<name\>
- Description: Returns the javascript to visualise a chart. **chart-code** redirects here. Normally this does not need
  to be called manually
- methods: [GET]
- GET:
    - Returns:
        - Format: Javascript
        - Type: octet-stream
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
        - 'datasource_name':
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
        - 'datasource_name':
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

## sharegroup-add

- url: groups
- Description: List sharegroups available to you or create a new one
- methods: [GET, POST]
- GET:
    - Returns:
        - Format: JSON
        - Type: [ShareGroup]
        - Code: 200
- POST:
    - Parameters:
        - 'name':
            - Description: Name of new sharegroup
            - Type: string
        - 'is_public':
            - Description: Privacy setting of new sharegroup
            - Type: boolean
            - Default: false
        - 'group_admins':
            - Description: List of user IDs of users with privileged group access
            - Type: [uuid]
            - Default: []
        - 'group_members':
            - Description: List of user IDs of users with group access
            - Type: [uuid]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: ShareGroup
        - Code: 200

## sharegroup-get

- url: groups/\<pk\>
- Description: Retrieve or delete a sharegroup
- methods: [GET, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: [ShareGroup]
        - Code: 200
- POST:
    - Returns:
        - Code: 204

## sharegroup-properties

- url: groups/\<pk\>/properties
- Description: Retrieve or alter sharegroup members, requires elevated permissions on the group
- methods: [GET, PATCH, DELETE]
- GET:
    - Returns:
        - Format: JSON
        - Type: ShareGroup
        - Code: 200
- PATCH:
    - Parameters:
        - 'group_admins':
            - Description: List of user IDs of users with privileged group access
            - Type: [uuid]
            - Default: []
        - 'group_members':
            - Description: List of user IDs of users with group access
            - Type: [uuid]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: ShareGroup
        - Code: 200
- DELETE:
    - Parameters:
        - 'group_admins':
            - Description: List of user IDs of users with privileged group access
            - Type: [uuid]
            - Default: []
        - 'group_members':
            - Description: List of user IDs of users with group access
            - Type: [uuid]
            - Default: []
    - Returns:
        - Format: JSON
        - Type: ShareGroup
        - Code: 200

## token_obtain

- url: token/
- Description: See drf-jwt documentation for obtain_jwt_token. Serves as login endpoint

## token_refresh

- url: token/refresh/
- Description: See drf-jwt documentation for refresh_jwt_token. Token will be copied from cookie to request object by
  middleware

## token_verify

- url: token/verify/
- Description: See drf-jwt documentation for verify_jwt_token. Token will be copied from cookie to request object by
  middleware

## token_blacklist

- url: token/blacklist/
- Description: See drf-jwt documentation for BlacklistView. Serves as logout endpoint. Middleware will tell client to
  remove token.

## get_current_user

- url: user/me/
- Description: Get the current user and update unprivileged information
- methods: [GET, PATCH]
- GET:
    - Returns:
        - Format: JSON
        - Type: User
        - Code: 200
- PATCH:
    - Parameters:
        - 'username':
            - Description: Display name
            - Type: string
            - Default: Previous value
        - 'first_name':
            - Description: First name
            - Type: string
            - Default: Previous value
        - 'last_name':
            - Description: Last name
            - Type: string
            - Default: Previous value
        - 'real_name':
            - Description: Flag indicating if first_name and last_name should generally be served on lookup and used for
              user search
            - Type: boolean
            - Default: Previous value
        - 'public_profile':
            - Description: Flag indicating if profile should turn up in search. Private profiles are still searchable by
              full id
            - Type: boolean
            - Default: Previous value
    - Returns:
        - Format: JSON
        - Type: User
        - Code: 200

## change_password

- url: user/me/password/
- Description: Change the password of the current user
- methods: [POST]
- POST:
    - Parameters:
        - 'oldPassword':
            - Description: Former password, used to reauthenticate the user for this sensitive request
            - Type: string
        - 'newPassword':
            - Description: New password
            - Type: string
    - Returns:
        - Code: 200

## change_email

- url: user/me/email/
- Description: Send an e-mail change request for the current user
- methods: [POST]
- POST:
    - Parameters:
        - 'password':
            - Description: Current password, used to reauthenticate the user for this sensitive request
            - Type: string
        - 'newEmail':
            - Description: New e-mail. This mail will receive a verification e-mail.
            - Type: e-mail
    - Returns:
        - Code: 200

## get_user

- url: user/id/\<pk\>
- Description: Retrieve a user object by its id
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: User
        - Code: 200

## search_user_by_name

- url: user/search/
- Description: Retrieve a user object by its id
- methods: [GET]
- GET:
    - Returns:
        - Format: JSON
        - Type: User
        - Code: 200

## get_users

- url: user/
- Description: Get multiple user objects for an array of uuid
- methods: [POST]
- POST:
    - Parameters:
        - 'users':
            - Description: List of user uuids
            - Type: [uuid]
    - Returns:
        - Format: JSON
        - Type: [User]
        - Code: 200

## iniate_password_reset

- url: password/reset/
- Description: Try to create a password reset request. This request will return 200 even if the provided mail is not
  associated with any accounts
- methods: [POST]
- POST:
    - Parameters:
        - 'email':
            - Description: E-Mail address of the account in question
            - Type: [uuid]
    - Returns:
        - Code: 200

## do_password_reset

- url: password/reset/\<reset_id\>/
- Description: Change the password as recovery. The GET-Endpoint is not an API-Endpoint, but a minimal password change
  page
- methods: [GET, POST]
- GET:
    - Returns:
        - Code: 200
- POST:
    - Parameters:
        - 'password':
            - Description: The new password to set for the account associated with this reset
            - Type: string
    - Returns:
        - Code: 200

## confirm_email

- url: email/confirm/\<token\>/
- Description: Confirm the password change request, verifying the user has access to the new e-mail address
- methods: [GET]
- GET:
    - Returns:
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
- 'datasource_name':
    - Description: Object name for displaying/ordering elements in UI
    - Type: string
- 'owner'
    - Description: Database id of owner
    - Type: uuid
- 'creation_time'
    - Description: Timestamp of when this datasource was created
    - Type: string
- 'modification_time'
    - Description: Timestamp of when this datasource was last modified
    - Type: string

## Chart

- 'id':
    - Description: Database id of chart
    - Type: int
- 'chart_type':
    - Description: Name of the chart type to be used, see pive for list of allowed values
    - Type: string
- 'chart_name':
    - Description: Object name for displaying/ordering elements in UI
    - Type: string
- 'owner'
    - Description: Database id of owner
    - Type: uuid
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
- 'creation_time'
    - Description: Timestamp of when this chart was created
    - Type: string
- 'modification_time'
    - Description: Timestamp of when this chart was last modified
    - Type: string

## ShareGroup

- 'id':
    - Description: Group ID
    - Type: int
- 'owner':
    - Description: ID of the group creator, can currently not be changed afterwards
    - Type: uuid
- 'name':
    - Description: Display name of this group
    - Type: string
- 'group_admins':
    - Description: List of user IDs of users with privileged group access
    - Type: [uuid]
- 'group_members':
    - Description: List of user IDs of users with group access
    - Type: [uuid]
- 'is_public':
    - Description: List of user IDs of users with group access
    - Type: boolean
    - Default: false

## Shares

- 'users':
    - Description: List of user IDs this share applies to
    - Type: [uuid]
    - Default: []
- 'groups':
    - Description: List of group IDs this share applies to
    - Type: [int]
    - Default: []

## User

- 'id':
    - Description: Database id
    - Type: uuid
- 'username':
    - Description: Display name
    - Type: string
- 'email':
    - Description: E-Mail address linked to the account, login name
    - Type: e-mail
- 'first_name':
    - Description: First name
    - Type: string
    - Default: ""
- 'last_name':
    - Description: Last name
    - Type: string
    - Default: ""
- 'real_name':
    - Description: Flag indicating if first_name and last_name should generally be served on lookup and used for user
      search
    - Type: boolean
    - Default: false
- 'public_profile':
    - Description: Flag indicating if profile should turn up in search. Private profiles are still searchable by full id
    - Type: boolean
    - Default: false

