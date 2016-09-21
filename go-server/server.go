package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"encoding/json"
	"net/http"

	"crypto/rand"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

const (
	UUID_SIZE = 16
)

type DownloadResponse struct {
	Url string `json:"url"`
}

type UploadResponse struct {
	Key string `json:"key"`
	Url string `json:"url"`
}

func oopsie(msg string) {
	log.Fatal(msg)
	os.Exit(1)
}

func uuid4() string {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		panic(err)
	}
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%12x", buf[0:4], buf[4:6], buf[6:8],
		buf[8:10], buf[10:16])
}

func api_download(w http.ResponseWriter, r *http.Request) {
	bucket := os.Getenv("S3_BUCKET")
	region := os.Getenv("AWS_REGION")

	key := r.URL.Query().Get("key")
	log.Printf("Download request for '%v'", key)

	svc := s3.New(session.New(&aws.Config{Region: aws.String(region)}))
	resp, err := svc.HeadObject(&s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		log.Println("Failed to get object", err)
	}

	req, _ := svc.GetObjectRequest(&s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	url, err := req.Presign(15 * time.Minute)

	if err != nil {
		log.Println("Failed to sign request", err)
	}

	w.Header().Set("Content-Type", "application/json")
	response := DownloadResponse{Url: url}
	json.NewEncoder(w).Encode(response)
}

func api_upload(w http.ResponseWriter, r *http.Request) {
	filename := r.URL.Query().Get("filename")
	log.Printf("Upload request for '%v'", filename)

	key := uuid4()
	bucket := os.Getenv("S3_BUCKET")
	region := os.Getenv("AWS_REGION")

	svc := s3.New(session.New(&aws.Config{Region: aws.String(region)}))
	req, _ := svc.PutObjectRequest(&s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
		ACL:    aws.String("private"),
		Metadata: map[string]*string{
			"filename": aws.String(filename),
		},
	})
	url, err := req.Presign(15 * time.Minute)

	if err != nil {
		log.Println("Failed to sign request", err)
	}

	w.Header().Set("Content-Type", "application/json")
	response := UploadResponse{Key: key, Url: url}
	json.NewEncoder(w).Encode(response)
}

func main() {
	fmt.Println("Starting server")
	http.HandleFunc("/api/download", api_download)
	http.HandleFunc("/api/upload", api_upload)
	log.Fatal(http.ListenAndServe(":5000", nil))
}
