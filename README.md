# MagicFlow

MagicFlow is a workflow automation system that uses Kafka for message processing and job execution. It provides a flexible framework for handling various types of jobs and workflows with support for different cloud providers.
[Documentation](https://cto2bpublic.github.io/magicflow-docs/) 

## Features

- Kafka-based message processing
- Support for multiple cloud providers (AWS, GCP)
- SSM (Systems Manager) integration for parameter management
- GitLab pipeline integration
- Extensible job system
- Configurable workflow controls

## Architecture

The system consists of several key components:

### Messaging System
- Uses Kafka for message processing
- Implements both command and event message patterns
- Supports message validation and error handling

### Job System
- Dynamic job loading and registration
- Support for various job types:
  - SSM operations (list, update parameters)
  - Pipeline management
  - Custom jobs

### Cloud Integration
- AWS SSM support
- GCP parameter management
- Cloud-agnostic design

## Setup

### Prerequisites
- Python 3.x
- Kafka cluster
- Cloud provider credentials (AWS/GCP)
- GitLab access (for pipeline features)

### Configuration
The system uses environment variables for configuration:

```bash
APP_LOGLEVEL=debug
APP_BOOTSTRAP_SERVERS=kafka-bootstrap:9093
PYTHONASYNCIODEBUG=1
CLOUD=aws
ENVIRONMENT=development
STAGE=dev
```

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment variables
4. Start the application:
```bash
python -m magicflow.app
```

## Job Types

### SSM Jobs
- `ssm_list_all`: List all parameters in a namespace
- `ssm_list`: List specific parameters
- `ssm_update`: Update parameter values

### Pipeline Jobs
- `check_pipeline_status`: Monitor pipeline execution
- `check_pipeline_job_status`: Check specific job status
- `play_pipeline_job`: Trigger pipeline job execution

## Development

### Adding New Jobs
1. Create a new Python file in `magicflow/jobs/lib/`
2. Use the `@j.register` decorator to register your job
3. Implement the job function with proper input validation

Example:
```python
@j.register("my_job")
def my_job(context: Jobs, cmd: CommandMessage):
    # Job implementation
    return workflow_success("Job completed")
```

### Message Format
Commands and events follow a specific JSON schema:

```json
{
  "id": "uuid",
  "attributes": {
    "source": "string",
    "type": "string",
    "date": "timestamp"
  },
  "data": {
    "name": "string",
    "input": {},
    "workflow_id": "string",
    "job_id": "string"
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

GPL-3.0 license

