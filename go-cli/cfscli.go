package main

import (
	"bytes"
	"fmt"
	"io"
	"os"
	//"time"
	//"strconv"

	"encoding/base64"
	"encoding/json"
	"io/ioutil"
	"net/http"
	"net/url"
	"path/filepath"

	"crypto/rand"
	"crypto/sha256"

	// External deps
	// Check the code in $GOPATH after running 'go get'
	"github.com/bgentry/speakeasy"       // This is not much code. Can be easily integrated.
	"golang.org/x/crypto/nacl/secretbox" // This is official (as far as I can tell), but in a separate repository
)

const (
	KEY_SIZE   = 32
	NONCE_SIZE = 24

	BASE_URL = "http://localhost:5000"
)

type Upload_info struct {
	Url string
	Key string
}

type Download_info struct {
	Url string
}

func usage(name string) {
	fmt.Println("Cloud Crypto File Cloud Storage for the Cloud(tm) Go Command Line Client (CCFCSCGCLC)")
	fmt.Println("")
	fmt.Printf("Usage: %v (upload|download) [...]\n", name)
	fmt.Printf("   %v upload filename - Upload the file 'filename'\n", name)
	fmt.Printf("   %v download key - Upload the file with key 'key'\n", name)
}

func oopsie(msg string) {
	fmt.Fprintf(os.Stderr, "%v\n", msg)
	os.Exit(1)
}

func create_nonce() (*[NONCE_SIZE]byte, error) {
	nonce := new([NONCE_SIZE]byte)
	_, err := io.ReadFull(rand.Reader, nonce[:])
	if err != nil {
		return nil, err
	}
	return nonce, nil
}

func upload(file string, password string) {
	filename := filepath.Base(file)

	cipher_key := sha256.Sum256([]byte(password))

	nonce, err := create_nonce()
	if err != nil {
		oopsie(err.Error())
	}

	encrypted_filename := make([]byte, len(nonce))
	copy(encrypted_filename, nonce[:])
	encrypted_filename = secretbox.Seal(encrypted_filename, []byte(filename), nonce, &cipher_key)
	encoded_filename := base64.StdEncoding.EncodeToString(encrypted_filename)

	data, err := ioutil.ReadFile(file)
	if err != nil {
		oopsie(err.Error())
	}

	nonce, err = create_nonce()
	if err != nil {
		oopsie(err.Error())
	}

	encrypted_data := make([]byte, len(nonce))
	copy(encrypted_data, nonce[:])
	encrypted_data = secretbox.Seal(encrypted_data, data, nonce, &cipher_key)

	uri, err := url.ParseRequestURI(BASE_URL)
	uri.Path = "/api/upload"
	query_parameters := url.Values{}
	query_parameters.Set("filename", encoded_filename)
	uri.RawQuery = query_parameters.Encode()
	url_str := fmt.Sprintf("%v", uri)

	res, err := http.Get(url_str)
	if err != nil {
		oopsie(err.Error())
	}
	defer res.Body.Close()

	decoder := json.NewDecoder(res.Body)
	var jsondata Upload_info
	err = decoder.Decode(&jsondata)
	if err != nil {
		oopsie(err.Error())
	}

	url := jsondata.Url

	r := bytes.NewReader(encrypted_data)
	request, err := http.NewRequest("PUT", url, r)
	if err != nil {
		oopsie(err.Error())
	}

	request.Header.Set("x-amz-acl", "private")
	request.Header.Set("x-amz-meta-filename", encoded_filename)
	//request.Header.Set("expires", strconv.FormatInt(time.Now().Unix() + 60*60, 10)) // TODO: This should probably be datetime(now + 1 hour)

	client := &http.Client{}
	res, err = client.Do(request)
	if err != nil {
		oopsie(err.Error())
	}

	//defer res.Body.Close()
	//body, err := ioutil.ReadAll(res.Body)
	//fmt.Printf("%s\n", string(body))

	if res.StatusCode == http.StatusOK {
		fmt.Println("File uploaded.")
		fmt.Printf("Download URL: http://127.0.0.1:5000/download/%v\n", jsondata.Key)
	}
}

func download(key string, password string) {
	fmt.Println("Downloading file")

	cipher_key := sha256.Sum256([]byte(password))

	uri, err := url.ParseRequestURI(BASE_URL)
	uri.Path = "/api/download"
	query_parameters := url.Values{}
	query_parameters.Set("key", key)
	uri.RawQuery = query_parameters.Encode()
	url_str := fmt.Sprintf("%v", uri)

	res, err := http.Get(url_str)
	if err != nil {
		oopsie(err.Error())
	}
	defer res.Body.Close()

	decoder := json.NewDecoder(res.Body)
	var jsondata Download_info
	err = decoder.Decode(&jsondata)
	if err != nil {
		oopsie(err.Error())
	}

	url := jsondata.Url
	res, err = http.Get(url)
	if err != nil {
		oopsie(err.Error())
	}
	defer res.Body.Close()

	encoded_metadata := res.Header.Get("x-amz-meta-filename")
	metadata, err := base64.StdEncoding.DecodeString(encoded_metadata)
	if err != nil {
		oopsie(err.Error())
	}

	var nonce [NONCE_SIZE]byte
	copy(nonce[:], metadata)
	filename_bytes, ok := secretbox.Open(nil, metadata[NONCE_SIZE:], &nonce, &cipher_key)
	if !ok { // Thanks for returning a bool instead of an error object :( Super intuitive!
		oopsie(err.Error())
	}
	filename := string(filename_bytes)

	file, err := os.Create(filename)
	if err != nil {
		oopsie(err.Error())
	}
	defer file.Close()

	_, err = io.Copy(file, res.Body)
	if err != nil {
		oopsie(err.Error())
	}

	fmt.Printf("File saved as '%v'\n", filename)
}

func main() {
	prog := os.Args[0]

	if len(os.Args) != 3 {
		usage(prog)
		os.Exit(1)
	}

	verb := os.Args[1]
	object := os.Args[2]

	password, err := speakeasy.Ask("Password: ")
	if err != nil {
		oopsie(err.Error())
	}

	switch verb {
	case "upload":
		upload(object, password)
	case "download":
		download(object, password)
	default:
		usage(prog)
		os.Exit(1)
	}
}
