# Requirements

## Frontend

### Specifications

#### Paper List

- Show list of papers.
- Able to set what to show in list.
- Able to filter papers by tags, authors, date, etc.

#### Reading Assistance

- Text are shown in text data.
    - not on PDF or image.
- The original figures and tables are shown alongside the text.
- Equations are shown by MathJax.
- Able to change view style
    - font size
    - line height
    - font family
    - color set
    - margin size
- Able to fly to sections headers from section list.

##### Highlighting
- Text can be highlighted.
    - Highlights are saved in server.
    - Each highlights can have notes.
    - highlights list
        - can fly to the specified position from the highlights list.
    - highlight colors can be changed.
        - There is color presets.
            - Able to edit
        - Able to set default highlight color.
            - (Do not have to choose color every time.)

#### Meta data edit
- form to edit meta data of the paper.

#### Trasnlation Assistance
- can switch language of the text.
    - the traslation data is stored in server.
    - Able to select language.
        - show available languages differs by paper.
- Able to show translation per paragraph.
    - The translation is shown as popup

#### Summary Assistance
- show summary of the paper.
    - summary data is stored in server.
    - Able to show summary per chapter if supported.

#### Chat Assistance
- Simple chat interface for LLM to ask questions about the paper.
    - The chat data is NOT stored in server.

#### Upload Paper
- form to upload PDF of paper.
    - The PDF is sent to backend server for processing.

### Technologies
- React + TypeScript
- Static websie
- Create SOLID class, component structure.
- Material UI design

## Backend Server

### Specifications
- create text data from PDF
    - This creates:
        - text data with structure information (sections, paragraphs, etc.)
        - figures and tables data
        - equations data
        - translation data
            - Able to select language
        - summary data
            - Able to select by-chapter summary or whole paper summary.
    - All created by LLM
    - meta data created here:
        - title
        - authors
        - very short description
        - tags
        - original URL

- Data storage and management
    - stores:
        - paper meta data
        - text data
        - figures and tables data
        - equations data
        - translation data
        - summary data
        - highlights data
    - provides API to frontend to:
        - fetch each data
        - update meta data
        - update highlights data
        - relay LLM chat.

- Need authentication to access API.

### Technologies
#### Coding
- C# (.NET 10)
    - SOLID class structure
    - Clean Architecture
    - AWS Lambda compatible
    
#### Infrastructure
- AWS
    - API Gateway
    - Lambda
    - DynamoDB
    - Cognito
        - Third party authentication by Google
    - bedrock
        - use Claude Haiku 4.5
- Only for one user lives in Tokyo.
