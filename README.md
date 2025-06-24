# Docklens: Advanced Image Processing Platform

Docklens is a full-stack, containerized image processing platform that provides robust APIs and a modern web interface for uploading, transforming, and managing images. It supports advanced operations such as grayscale conversion, blurring, rotation, resizing, and background removal, with secure authentication and persistent storage.

## Features mapped with Conversations

- **Conversation 1**
  - Project structure
  - Upload feature
  - Grayscale feature
  - Docker file
  - Swagger support
  
  **Screenshots:**
  - [Grayscale](https://drive.google.com/file/d/151UU1MVlpUd46HL4xh4mLUf4d7KXHxn7/view?usp=sharing)
  - [Swagger Integration](https://drive.google.com/file/d/1xq9vIyaM6ZUDgZegaDW3wzpuodUwqrHl/view?usp=sharing)

- **Conversation 2**
  - Added MongoDB to Docker Compose
  - Added Redis to Docker Compose
  - Configured Docker Health Checks
  - Tested Communication & Persistence
  - Integrated MongoDB with Flask app
  - Integrated Redis (perceptual hash caching) with Flask app
  
  **Screenshot:**

- **Conversation 3**
  - Implemented following features:
    - Blur
    - Rotate
    - Resize
    - Background Removal
  - Implemented a Unified Endpoint for all transformation features.
  
  **Screenshots:**
  - [Blur](https://drive.google.com/file/d/1G2D5cwm7tBOvzQBO4YOBaWfGnWzPBdqI/view?usp=share_link)
  - [Resize](https://drive.google.com/file/d/1aSB4DIEik7UfxkPjJCgT1aBPdaYj8dTC/view?usp=share_link)
  - [Rotate](https://drive.google.com/file/d/1Pxs2g8Lsey__PfZ9shfo3FoXCdiClmFX/view?usp=share_link)
  - [Background Removal](https://drive.google.com/file/d/12DKK5O_gBB8idAMDgaFmhiWCVOXgvBde/view?usp=share_link)

- **Conversation 4**
  - Implemented image versioning system to store several processed versions of the same image.
  - Changes:
    - mongodb_service.py
    - redis_service.py
    - image_endpoints.py
    - image_processor.py
  
  **Screenshots:**
  - [Image Versioning](https://drive.google.com/file/d/144Vcgt7kEFbowf1mzq9ceMhOXGeOqwuR/view?usp=share_link)

- **Conversation 5**
  - Implemented auth microservice (auth-service)
  
  **Screenshots:**
    - [Health](https://drive.google.com/file/d/1tZcZS_1yiGOFttnKW_0XPQAozaYrVd0O/view?usp=share_link)
    - [Register](https://drive.google.com/file/d/1Vr8yE-W0k99SmjvF34cyIdVBbmlGaFRH/view?usp=share_link)
    - [Login](https://drive.google.com/file/d/1FKU3gVJMZQURCI_df4W64p2VUIHYOVrN/view?usp=share_link)
    - [Logout](https://drive.google.com/file/d/14VQSkzc-vCvmzJDdsjKyUtSbq_EngWER/view?usp=share_link)

- **Conversation 6**
  - Implemented API documentation for auth-service
  - Integrated auth-service with image processing endpoints

- **Conversation 7**
  - Implemented React JS Frontend for the image processing platform.
  
  **Screenshots:**
    - [Register](https://drive.google.com/file/d/1oc6nYiftr-GVaEimExWVSrL3IyJkW_BW/view?usp=share_link)
    - [Login](https://drive.google.com/file/d/1_leZY8JVD71pGTUx3OVxrlmydrvehI64/view?usp=share_link)
    - [Dashboard](https://drive.google.com/file/d/1zxHqoYP2SFtkCs2nqsDVLbYq82PC5DJs/view?usp=share_link)

- **Conversation 8**
  - Deployment and optimization of the platform

  **Link:**
  - [Docker Hub](https://drive.google.com/file/d/1N0zz55EKbJFP5ejhvPZYFAovCyBNndzH/view?usp=share_link)

## Unit Test Screenshots

- [Grayscale Unit Test](https://drive.google.com/file/d/1ARpcEFjRdebxrqvVDs9gLiOG79RhIX92/view?usp=share_link)
- [MongoDB/Redis Unit Test](https://drive.google.com/file/d/1smJGC5ErZr_qkyD45hd9sQYgmwvV4ob8/view?usp=share_link)
- [Transformations Unit Test](https://drive.google.com/file/d/1n-ihPRCBwBCojNejlJVysEIQ_YXvCsPd/view?usp=share_link)
- [Image Versioning Unit Test](https://drive.google.com/file/d/1R19643fqggZ0VqABLIDquRiOdfHe03lZ/view?usp=share_link)
- [Auth Service Unit Test](https://drive.google.com/file/d/1t_s67JNW2OlraRP1g_s9T1coYIUmJQwa/view?usp=share_link)
- [Frontend Register Unit Test](https://drive.google.com/file/d/1ZqVSkovtChtdbp6Ekmp5UBVlI7Kg4jBW/view?usp=share_link)

## Project Structure

```
├── app/                # Main backend (Flask) application
│   ├── api/            # API endpoints and routes
│   ├── core/           # Image processing logic
│   ├── models/         # Data models
│   ├── services/       # MongoDB/Redis services
│   ├── middleware/     # Auth middleware
│   ├── utils/          # Helpers and logging
│   ├── static/         # Static files (processed images)
│   ├── logs/           # Log files
│   └── main.py         # App entry point
│
├── auth-service/       # Authentication microservice (Flask)
│   ├── app/            # Auth API, models, services
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/           # React frontend
│   ├── src/            # React source code
│   ├── public/         # Static assets
│   ├── package.json
│   └── Dockerfile
│
├── tests/              # Backend tests (pytest)
├── scripts/            # Utility scripts
├── uploads/            # Uploaded images
├── docker-compose.yml  # Multi-service orchestration
├── Dockerfile          # Main app Dockerfile
└── README.md
```

## Prerequisites

- Docker & Docker Compose
- Node.js (v14+ for frontend development)
- npm (v6+ for frontend development)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd docklens
   ```

2. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

   This will start the backend API, authentication service, frontend, MongoDB, and Redis.

3. **(For local frontend development):**
   ```bash
   cd frontend
   npm install
   npm start
   ```

## Running the Application

- **Backend API:** http://localhost:5001
- **Auth Service:** http://localhost:5002
- **Frontend UI:** http://localhost:5003

## Testing

- **Backend tests:**
  ```bash
  pytest tests/
  ```
- **Frontend tests:**
  ```bash
  cd frontend
  npm test
  ```

## Technologies Used

- **Backend:**
  - Python
  - Flask
  - Gunicorn
  - MongoDB
  - Redis
  - Pillow
  - Rembg
  - ONNX
  - Torch
- **Auth Service:**
  - Python
  - Flask
  - JWT
  - MongoDB
- **Frontend:**
  - React
  - Axios
  - Sass
  - Webpack
  - Jest
- **Containerization:**
  - Docker
  - Docker Compose

## API Documentation

Interactive API docs are available at:  
- **Backend:** http://localhost:5001/docs  
- **Auth Service:** http://localhost:5002/docs

## Final Project Demo and Outcome

[Link to Screen Recording](https://drive.google.com/file/d/1kKutMFphlliY4u6TZeg9uJSdxq1gLRmL/view?usp=share_link)

## Project Outcome

Docklens enables users to securely upload, process, and manage images with advanced transformations, persistent history, and a modern UI. Its microservice architecture and containerization make it scalable and easy to deploy in any environment.
