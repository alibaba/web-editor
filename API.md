# WEditor
Editor Driver for ATX

Port: 17310

To memorize the create day: 2017/03/10

# Installation
```
pip install weditor
```

# Usage
```
python -m weditor
```

# API
### Get Version
This method returns local server version

```
GET /api/v1/version
```

#### Response
Status: 200

```json
{
	"name": "0.0.2"
}
```

## File API

### Get contents
This method returns the contents of a file or directory in a repository

```
GET /api/v1/contents/:path
```

#### Response if content is a file
Status: 200 OK

```json
{
  "type": "file",
  "encoding": "base64",
  "size": 5362,
  "name": "README.md",
  "path": "README.md",
  "content": "encoded content ...",
  "sha": "3d21ec53a331a6f037a91c368710b99387d012c1"
}
```

#### Response if content is a directory
Status: 200 OK

```json
[
	{
	  "type": "file",
	  "size": 5362,
	  "name": "README.md",
	  "path": "README.md",
	  "sha": "3d21ec53a331a6f037a91c368710b99387d012c1"
	},
	{
	  "type": "dir",
	  "size": 0,
	  "name": "foo",
	  "path": "foo",
	}
]
```


### Create a file
This method creates a new file in repository

```
POST /api/v1/contents/:path
```

#### Example Input
```json
{
  "content": "bXkgbmV3IGZpbGUgY29udGVudHM="
}
```

#### Response
Status: 201 Created

```json
{
	"content": {
		"type": "file",
		"name": "hello.txt",
		"path": "notes/hello.txt",
		"sha": "95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
		"size": 9
	}
}
```

## Device API
### Get device list
This method returns devices connected to PC

```
GET /api/v1/devices
```

### Get current using device
```
GET /api/v1/user/device
```

### Set current using device
```
PUT /api/v1/user/device
```

#### Example Input
```json
{
	"serial": "cff12345"
}
```

### Get device screenshot
```
GET /api/v1/devices/:serial/screenshot
```

#### Response
```json
{
	"type": "jpeg",
	"data": "bXkgbmV3IGZpbGUgY29udGVudHM"
}
```

#### Response if error
Status: 403

```json
{
	"description": "Some reason"
}
```

### Get UIView
Get uiview with json response

```
GET /api/v1/devices/{serial}/uiview
```

#### Response
Status: 200

Every node will always has an `id` field. iOS and Android got the some response structure.


```json
{
	"nodes": [{
		"id": 0,
		"text": "Hello",
		"description": "hello",
		"other...": "..."
	}, {
		"id": 1,
		"other...": ".."
	}]
}
```

## Python Debug WebSocket API
### Run code
This method run and get the live output

```
WebSocket CONNECT /api/v1/build
```

SEND json data

```json
{
	"content": "print('hello')"
}
```

RECV json data when running

```json
{
	"buffer": "hello"
}
```

RECV json data when finished. __duration unit is ms.__

```json
{
	"buffer": "end ...",
	"result": {
		"duration": 1002,
		"exitCode": 1
	}
}
```

# LICENSE
[MIT](LICENSE)
