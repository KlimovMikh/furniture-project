This project utilizes possibilities of SpaCy library for Named Entity Recognition task. Namely, this app extracts names of products from a given URL that points to a certain furniture store website.
In "app" directory, the application itself is located. It is ready to launch on your localhost, you have to run "go run app/main.go" to start local server.
In "url-processor" directory, the url processor component is located, written in Go. Its task is to process a dataset of URLs that were used for training the model.
In "training" diractory, everything related to NER model is located: datasets used, several preprocessing scripts and a pipeline for training.

The application is available for deployment from Docker Hub. You can pull an image using the following command: "docker pull klimovmikh/furniture-project:latest".
