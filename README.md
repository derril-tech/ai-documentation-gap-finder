# AI Documentation Gap Finder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-20.x-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org/)

## 🎯 What is AI Documentation Gap Finder?

**AI Documentation Gap Finder** is an intelligent, automated system that identifies gaps between your codebase and documentation, then generates high-quality documentation drafts to fill those gaps. It's designed to help development teams maintain comprehensive, up-to-date documentation with minimal manual effort.

## 🚀 What does it do?

The system performs comprehensive analysis across your entire codebase and documentation to:

### 🔍 **Gap Detection**
- **Code Analysis**: Extracts symbols, functions, classes, and APIs from TypeScript/JavaScript, Python, OpenAPI specs, GraphQL schemas, and CLI tools
- **Documentation Analysis**: Parses existing MD/MDX documentation to understand current coverage
- **Mapping**: Uses AI-powered semantic matching to identify undocumented code elements
- **Drift Detection**: Monitors for API changes, broken links, and outdated documentation

### 📊 **Intelligent Scoring**
- **Readability Metrics**: Analyzes documentation quality using Flesch scores and layout heuristics
- **Completeness Assessment**: Evaluates coverage of parameters, examples, and edge cases
- **Freshness Tracking**: Identifies outdated documentation based on code changes
- **Example Density**: Measures the ratio of code examples to documentation

### ✍️ **Auto-Drafting**
- **Smart Content Generation**: Creates MDX documentation drafts with proper structure
- **Code Examples**: Generates request/response examples and code snippets
- **Visual Elements**: Includes Mermaid diagrams, tables, and formatted content
- **Context Awareness**: Incorporates related documentation and cross-references

### 📈 **Telemetry & Insights**
- **Usage Analytics**: Tracks API endpoint usage, 404 errors, and search patterns
- **Gap Prioritization**: Prioritizes documentation needs based on usage data
- **Performance Monitoring**: Identifies high-error endpoints and user pain points
- **Recommendations**: Provides actionable insights for documentation improvement

### 🔄 **Export & Integration**
- **PR Generation**: Creates pull requests with documentation updates
- **Bundle Exports**: Generates comprehensive reports in JSON/PDF formats
- **Git Integration**: Supports GitHub and GitLab with proper branch naming and changelogs
- **Preview Links**: Provides preview URLs for draft review

## 💡 Benefits

### 🎯 **For Development Teams**
- **Save Time**: Reduce manual documentation writing by 80%+
- **Improve Quality**: Ensure comprehensive, up-to-date documentation
- **Reduce Support**: Fewer questions from users due to better documentation
- **Onboard Faster**: New team members can understand codebase quickly

### 🏢 **For Organizations**
- **Reduce Technical Debt**: Keep documentation in sync with code changes
- **Improve Developer Experience**: Better internal tools and API documentation
- **Compliance**: Maintain audit trails and documentation standards
- **Scalability**: Handle large codebases and multiple projects efficiently

### 👥 **For Users**
- **Better APIs**: Comprehensive documentation with working examples
- **Faster Integration**: Clear, accurate information for implementation
- **Reduced Errors**: Up-to-date parameter lists and error handling
- **Self-Service**: Find answers without contacting support

## 🏗️ Architecture

The system is built as a microservices architecture with:

- **API Gateway** (NestJS): RESTful API with authentication and RBAC
- **Frontend** (Next.js): Modern React UI with real-time dashboards
- **Workers** (Python): Specialized microservices for different analysis tasks
- **Infrastructure**: PostgreSQL with pgvector, Redis, NATS, and MinIO
- **Observability**: OpenTelemetry, Sentry, and Prometheus monitoring

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20.x
- Python 3.11

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/ai-documentation-gap-finder.git
   cd ai-documentation-gap-finder
   ```

2. **Start the infrastructure**
   ```bash
   make up
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:3001
   - MinIO Console: http://localhost:9001 (admin/admin)

### Configuration

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Database Setup**
   ```bash
   # The database will be automatically initialized
   # Check logs: docker-compose logs db
   ```

3. **Add Your First Project**
   - Navigate to http://localhost:3000
   - Create an organization and project
   - Add your repository URL
   - Start the analysis

## 📖 Usage

### 1. **Project Setup**
- Create an organization and project in the web interface
- Configure repository access (GitHub/GitLab integration)
- Set up documentation preferences and templates

### 2. **Analysis**
- The system automatically clones and analyzes your codebase
- Workers process code, documentation, and create mappings
- Gap analysis identifies missing or outdated documentation

### 3. **Review & Edit**
- Use the Gap Explorer to review identified issues
- Check the Drift Analysis for API changes
- Review auto-generated drafts in the Draft Studio

### 4. **Export & Deploy**
- Generate pull requests for documentation updates
- Export comprehensive reports for stakeholders
- Monitor telemetry for ongoing improvements

## 🔧 Development

### Project Structure
```
├── api/                 # NestJS API Gateway
├── frontend/           # Next.js Frontend
├── workers/            # Python Microservices
│   ├── clone/         # Repository cloning
│   ├── scan-code/     # Code analysis
│   ├── scan-docs/     # Documentation parsing
│   ├── map/           # Code-doc mapping
│   ├── diff/          # Drift detection
│   ├── score/         # Quality scoring
│   ├── draft/         # Content generation
│   ├── export/        # Export functionality
│   └── telemetry/     # Usage analytics
├── scripts/           # Database and setup scripts
└── docker-compose.yml # Infrastructure configuration
```

### Development Commands
```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down

# Restart services
make restart

# Clean up
make clean
```

### Adding New Workers
1. Create a new directory in `workers/`
2. Add `main.py`, `requirements.txt`, and `Dockerfile`
3. Update `docker-compose.yml`
4. Implement NATS message handling

## 📊 Monitoring

### Health Checks
- API: http://localhost:3001/health
- Workers: Check Docker logs for health status
- Database: Automatic health checks in Docker Compose

### Metrics
- Prometheus metrics available at `/metrics` endpoints
- Grafana dashboards for visualization
- Sentry integration for error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code style and patterns
- Add tests for new functionality
- Update documentation for API changes
- Ensure all Docker services build successfully

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions for questions and ideas
- **Email**: support@ai-docgap.com

## 🙏 Acknowledgments

- Built with [NestJS](https://nestjs.com/) and [Next.js](https://nextjs.org/)
- Powered by [PostgreSQL](https://postgresql.org/) and [pgvector](https://github.com/pgvector/pgvector)
- Event-driven architecture with [NATS](https://nats.io/)
- Modern UI components with [shadcn/ui](https://ui.shadcn.com/)

---

**AI Documentation Gap Finder** - Making documentation effortless, comprehensive, and always up-to-date. 🚀
