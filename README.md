# SuperSuat - Paper Reading Assistance Application

A full-stack application for reading and managing academic papers with AI-powered assistance.

## Features

### Frontend (React + TypeScript)
- **Paper List**: Browse and filter papers by tags, authors, and search text
- **Reading Assistance**: 
  - Text displayed in clean format (not PDF)
  - MathJax equation rendering
  - Customizable view styles (font size, line height, font family, color theme)
  - Section navigation
- **Highlighting**: 
  - Text highlighting with notes
  - Color presets with default color setting
  - Highlight list navigation
- **Translation Assistance**: 
  - Switch between languages
  - Paragraph-level translation popups
- **Summary Assistance**: 
  - Paper-wide summaries
  - Chapter-by-chapter summaries
- **Chat Assistance**: Ask questions about the paper using AI
- **Paper Upload**: Upload PDFs for AI processing

### Backend (C# .NET 10)
- Clean Architecture with SOLID principles
- AWS Lambda-compatible API
- PDF processing with AI (Claude Haiku 4.5 via Bedrock)
- DynamoDB for data storage
- S3 for file storage
- Cognito for authentication (Google OAuth)

## Project Structure

```
SuperSuat/
├── Docs/
│   ├── Requirements.md
│   ├── ClassDiagram.md
│   ├── SequenceDiagram.md
│   └── DataStructure.md
├── backend/
│   ├── src/
│   │   ├── SuperSuat.Domain/        # Entities and enums
│   │   ├── SuperSuat.Application/   # Use cases, interfaces, DTOs
│   │   ├── SuperSuat.Infrastructure/# AWS implementations
│   │   ├── SuperSuat.Api/           # Lambda functions
│   │   └── SuperSuat.LocalApi/      # Local development API
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── services/
│   │   └── types/
│   └── Dockerfile
└── docker-compose.yml
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- .NET 10 SDK (for backend development)
- Node.js 22+ and pnpm (for frontend development)

### Local Development with Docker

1. Start all services:
```bash
docker-compose up -d
```

2. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - MinIO Console (S3): http://localhost:9001

### Manual Development

#### Backend
```bash
cd backend
dotnet restore
dotnet build
dotnet run --project src/SuperSuat.LocalApi
```

#### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

### Running Tests

#### Backend
```bash
cd backend
dotnet test
```

#### Frontend
```bash
cd frontend
pnpm test
```

## AWS Deployment

### Prerequisites
- AWS Account
- AWS CLI configured
- DynamoDB tables created
- S3 bucket created
- Cognito User Pool configured
- Bedrock access enabled

### Environment Variables (Lambda)
- `PAPERS_TABLE`: DynamoDB table name for papers
- `TRANSLATIONS_TABLE`: DynamoDB table name for translations
- `SUMMARIES_TABLE`: DynamoDB table name for summaries
- `HIGHLIGHTS_TABLE`: DynamoDB table name for highlights
- `HIGHLIGHT_PRESETS_TABLE`: DynamoDB table name for highlight presets
- `S3_BUCKET`: S3 bucket name
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `BEDROCK_MODEL_ID`: Bedrock model ID (default: anthropic.claude-3-5-haiku-20241022-v1:0)

### API Gateway Configuration
Configure API Gateway to route to Lambda functions:
- `GET /papers` → PaperFunctions::GetPapers
- `GET /papers/{paperId}` → PaperFunctions::GetPaper
- `POST /papers` → PaperFunctions::UploadPaper
- `PUT /papers/{paperId}` → PaperFunctions::UpdatePaper
- ... (see API documentation)

## API Documentation

See [DataStructure.md](Docs/DataStructure.md) for complete API endpoint documentation.

## Architecture

See [ClassDiagram.md](Docs/ClassDiagram.md) for class structure and [SequenceDiagram.md](Docs/SequenceDiagram.md) for operation flows.

## Technologies

### Backend
- C# / .NET 10
- AWS Lambda, API Gateway
- DynamoDB
- S3
- Cognito
- Bedrock (Claude Haiku 4.5)

### Frontend
- React 19
- TypeScript
- Material UI 7
- Vite
- React Router
- KaTeX (math rendering)

## License

MIT
