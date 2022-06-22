# MeSpam
Python script to move spam emails allegedly from "me" to the spam folder. This script uses IMAP to connect to your email. The matching algorithm is extremely specific to emails that have been flooding my inbox starting about June 2022. These emails appear to have been sent by my email address (or yours) and they contain several links to https://storage.googleapis.com.

## Configuration
Configure as many mailboxes as you need to process in the `mailboxes.yml` configuration file. The format is as follows:

```
mailboxes:
  john:
    email: john.doe@gmail.com
    password: 123456
    imap-host: imap.sample.com
    spam-folder: INBOX.Spam
  jane:
    email: jane.doe@gmail.com
    password: 789101
    imap-host: imap.sample.com
    spam-folder: INBOX.Spam
```
\* *Obviously you will need to modify the configuration in `mailboxes.yml` to meet your personal needs (i.e., the configuration of your IMAP mailboxes).*

## Running the Script
To run all configurations:
```
python mespam.yml
```

To run a specific configuration:
```
python mespam.yml john
```

### Running Using a Cron Job
* First clone the repository: git clone https://github.com/franzone/MeSpam.git MeSpam
* Second, modify MeSpam/mailboxes.yml appropriately
* Finally, create a crontab entry to run it:
```
# Runs every 15 minutes
*/15 * * * * cd $HOME/MeSpam && python3 mespam.py
```

## Requirements
* Python >= 3.10
* IMAP account that allows remote authentication using **email address** and **password**

## Terms and Conditions
Download and use of any content (files, scripts, images, etc.) from the repository located at https://github.com/franzone/MeSpam construes your consent to these **Terms and Conditions**. Use of this script or any related files is at your own risk. The author, Jonathan Franzone, his family, friends or associates, may not be held liable for any damages, imagined or real, caused by your use of this script or related files.

## Author
The author of this script is Jonathan Franzone (that's me!). You can find more information about him at:
* https://franzone.blog
* https://about.franzone.com
* https://www.linkedin.com/in/jonathanfranzone/

## License
[MIT License](LICENSE)