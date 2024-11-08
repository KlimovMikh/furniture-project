# Step 1: Build the Go application
FROM golang:1.20 AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy Go module files and download dependencies
COPY go.mod ./
RUN go mod download

# Copy the application files
COPY . .

COPY static /app/static

# Build the Go application
RUN go build -o server main.go

# Step 2: Set up the runtime environment
FROM python:3.10-slim

RUN pip install spacy

# Copy the built Go binary and Python script from the builder stage
WORKDIR /app
COPY --from=builder /app/server /app/server
COPY ner.py /app/ner.py

COPY processor /app/processor

COPY custom_ner_model_transferred /app/custom_ner_model_transferred

# Install any required Python packages (if needed)
# RUN pip install -r requirements.txt  # Uncomment if you have a requirements.txt

# Expose the port the Go server will run on
EXPOSE 8080

RUN chmod +x /app/processor

# Run the Go server
CMD ["/app/server"]
