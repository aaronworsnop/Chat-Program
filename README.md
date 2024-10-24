# Chat Program
## One-on-one chatting application written in Python
`Python` `Computer Networks` `TCP` `Encryption`

![image](https://github.com/user-attachments/assets/0a43f279-4ac0-4e7f-8060-edc815ebdaca)

### Installation
If you already have the source code installed, move onto *Running the Application.* Ensure that the project folder is unzipped.

*From the GitHub repository*
- Press "Code" on this GitHub page.
- "Download ZIP"
- Unzip the file


### Running the Application
- Move to the root directory of the project (where this `README.md` file sits).
- Open a terminal from this directory and run `python chat_server.py --port=X`, with `X` being a number from 1024–49151, like 1080.
- Open another terminal at this directory and run `python chat_client.py --port=X`.
    - Follow the instructions in the terminal.
- Repeat the previous step to create as many users as you like.  
  
#### Functionality
- To chat, simply write a message and press `ENTER`. The message will appear for other users.
- To exit the chatroom, close the terminal.

### Requirements
- Python Version 3.7 or later
- SSL 

*Since this is an example application, the `cert.pem`, which stores a generated key and certificate, is provided in this repository. In other cases it would be generate by yourself.*
