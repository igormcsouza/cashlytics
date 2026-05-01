# Cashlytics

Cashlytics helps you track, analyze, and optimize your finances in one place—giving you clear insights into your spending, income, and net worth.

## Features

- Create, view, edit, and delete expenses
- See the total sum of all expenses
- Mark expenses as recurrent or one-time
- Confirmation popup before deletion

## Tech Stack

- **Backend**: Python + Flask
- **Frontend**: Vue.js 3 (CDN) + Tailwind CSS (CDN), served as static files by Flask
- **Database**: MongoDB
- **Containerization**: Docker + docker-compose

## Project Structure

```
cashlytics/
├── backend/
│   ├── app.py              # Flask REST API
│   ├── requirements.txt
│   ├── Dockerfile
│   └── static/
│       └── index.html      # Vue.js single-page frontend
├── docker-compose.yml
└── README.md
```

## Running Locally

**Prerequisites**: [Docker](https://docs.docker.com/get-docker/) and [docker-compose](https://docs.docker.com/compose/install/)

```bash
docker-compose up
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

To rebuild after code changes:

```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint             | Description          |
|--------|----------------------|----------------------|
| GET    | `/expenses`          | List all expenses    |
| POST   | `/expenses`          | Create an expense    |
| PUT    | `/expenses/<id>`     | Update an expense    |
| DELETE | `/expenses/<id>`     | Delete an expense    |

### Expense Data Model

```json
{
  "description": "Electricity bill",
  "deadline": "2025-06-01",
  "value": 120.50,
  "recurrent": true
}
```
