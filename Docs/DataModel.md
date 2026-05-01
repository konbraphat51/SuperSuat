# Data Models

## Database Models

AWS DynamoDB is used for data storage. The following are the main data models used in the application.

### Paper

| Field Name  | Type      | Description                                       |
| ----------- | --------- | ------------------------------------------------- |
| id          | int       | PK: Unique identifier for the paper               |
| title       | str       | Title of the paper                                |
| authors     | list<str> | List of authors                                   |
| description | str       | Short description of the paper                    |
| tags        | list<str> | List of tags associated with the paper            |
| url         | str       | Original URL of the paper                         |
| created_at  | int       | Timestamp of when the paper was added (Unix time) |
| updated_at  | int       | Timestamp of the last update (Unix time)          |

###
