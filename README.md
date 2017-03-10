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

## Python Debug WebSocket API
### Run code
This method run and get the live output

```
CONNECT /api/v1/ipython/:path
```

#### Response
JSON line by line

At beginning

```json
{
	"section": "abcd"
}
```

Finally

```json
{
	"section": "",
	"duration": 1000223,
	"exit": 0
}
```

### Cancel run
Send JSON message to server

```json
{
	"stop": true
}
```

# LICENSE
[MIT](LICENSE)
