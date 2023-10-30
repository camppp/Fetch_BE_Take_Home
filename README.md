# Fetch_BE_Take_Home Receipt Processor App

A Flask-based API server that processes receipts and calculates reward points based on specific rules.

## Table of Contents

- [Features](#features)
- [Design Considerations](#design-considerations)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Testing](#testing)
- [Usage](#usage)

## Features

1. Process receipt API: Process uploaded JSON receipts and return the generated receipt UUID
- Validate the format and fields of the receipt JSON
- Calculate and store the reward points from the receipt according to certain rules
2. Get Points API: Allow the user to look up reward points for specific receipts by providing the receipt UUID
3. Concurrent request processing for both the process receipt and get points API
4. Extensive test suite written with pytest, and appropriate application error handling
5. Support for containerization with Docker

## Design Considerations
1. There could be a large number of concurrent requests for both APIs
   - Enable threading in the Flask application
   - Provide UUID for each receipt in order to eliminate race conditions
2. The process to calculate reward points should only happen once for each receipt 
   - Calculate reward points during the process receipt API, and store the result for future get points requests
   - On the other hand, if this is done during the get points API, the application will become very inefficient. Because it may cause a lot of repeated work
3. The get points API should be idempotent
4. The JSON receipt parameter in the process receipt API may contain invalid JSON structures, invalid types, and invalid field values
   - Validate the JSON receipt format as the first step in the process receipt API
   - Validate the JSON field value strings with Regex as the first step in each reward points calculation section
   - These two validation stages are separated to provide more flexibility when reward rules change
5. The application should be able to recover from failures, and the problem cause should be visible to the user
   - Provide accurate error messages, and use a centralized location to handle application errors, which then sends the corresponding status code to the user
6. The application should be well-tested, and should support many platforms
   - Implement a full test suite in pytest, and follow the TDD process
   - Containerize the application with Docker. This way, developers and users can easily run and deploy the application under different hardware and OS 

## Prerequisites

* python 3.10.11
* Flask 3.0.0
* pytest 7.4.3
* Docker

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/camppp/Fetch_BE_Take_Home.git
    ```

2. Navigate to the project directory:

    ```bash
    cd Fetch_BE_Take_Home
    ```

3. Install required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

4. Build Docker images for both the application and test suite

    ```bash
    docker build -f Dockerfile --tag receipt-processor-app .
    docker build -f Dockerfile.test --tag receipt-processor-app-test .
    ```

## Testing

Method 1 (Recommended)
  ```bash
  docker run receipt-processor-app-test
  ```

Method 2
  ```bash
  pytest test.py
  ```
   
## Usage Method 1 (Recommended)

1. Run the application using Docker
   
   ```bash
    docker run -d -p 5000:5000 receipt-processor-app
    ```

2. Send requests to the server
   - The default host is 127.0.0.1, and the default port is 5000 (They can be configured in app.py)
   - Sample request: http://127.0.0.1:5000/receipts/0d95b7e8-5f54-4aaa-9d53-fd1e819913e7/points

4. Press `Ctrl+C` to stop the application

## Usage Method 2

1. Run the application using Python
   
   ```bash
    python app.py
    ```

2. Send requests to the server
3. Press `Ctrl+C` to stop the application
