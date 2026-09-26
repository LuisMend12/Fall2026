# Unit 1: Project 1 - Catch Me if You Can!

> **Unit Tip:** Your Ubuntu VM is optional for Mac/Linux for this unit. If you don't have access set up yet, you can follow the instructions in Step 0 of the lab to Install Wireshark on your Mac or Linux local computer! The files you'll need for this project can be found below under Tasks.

> 🛑 **Do not run on a Windows machine.** The example `.pcap` files provided contain actual Windows malware, and if you extract these objects the malware will begin running on your computer! If you do not have access to a local Mac or Linux machine, please take the time to 🔗 set up an Ubuntu VM before completing this project.

## Overview

One of the most popular scams throughout industries is the Business Email Compromise (BEC). BECs are responsible for many notable real world scams, incurring $26 billion dollars of losses from 2016 to 2019 alone.

We'll be handling our own BEC situation, where a malicious actor (played by Leonardo DiCaprio) has sent phishing emails to many of our employees, trying to trick them into sending hundreds of thousands of dollars. To stop this, we'll be looking at some potentially malicious emails and inspecting `.pcap` files to determine which emails are legitimate and which ones are fraudulent.

## 🎯 Goals

By the end of this assignment, you will be able to...

- Inspect `.pcap` files and extract their email content
- Identify legitimate vs. fraudulent emails
- Correctly identify the malicious actor
- Understand why SMTP header metadata — not just email content — is the forensic anchor for tracing the origin of a phishing campaign

## 📘 Resources

- Reference guide for SMTP display filter commands in Wireshark
- Source of the malicious `.pcap` file

## ✉️ What You'll Turn In

For this assignment, you'll be filling and submitting a copy of the 📄 Project 1 Submission Template (Google Doc).

Before proceeding, we recommend you open it up now and read over the requirements in the document. It might be easier to "fill-as-you-go" than try to fill it all out after you complete the project.

### Required Challenges

Complete each task in the 🧩 Tasks section below.

To receive full credit, you must submit ...

- [ ] The malicious actor's IP address
- [ ] The subject lines of three different phishing emails you identified
  - Tip: only one of the `.pcap` files contains malicious emails
- [ ] A detailed explanation of how you found the malicious actor using the provided `.pcap` files

### Stretch Challenge

To receive bonus points, you can submit...

- [ ] Three different `.eml` files showing the content of the phishing emails you identified

⚠️ Potential Problem: Antivirus flagging the `.eml` files!

## 🧩 Tasks

1. Download the `pcap_files.zip` which contains multiple `.pcap` files taken on different days.
   - *AI opportunity:* Use AI to understand command line tools → `.zip` files
2. Use the Wireshark techniques for filtering packets you learned in the lab - as well as the SMTP reference guide - to inspect emails for malicious content.
3. Identify the malicious actor the emails are coming from.
4. Attempt the stretch goal (optional).

## 💡 Hints

- For help installing / accessing Wireshark, use the same techniques as in Step 0 of the lab.
- Click on a specific packet (or double-click to pop out a new window) to show additional information in the packet details and packet bytes panes at the bottom of your Wireshark interface.
- While a number of filters from the SMTP reference guide can help you filter down to find the phishing packets, we suggest you start with filters containing the word `data`, as you will have more data to inspect.
- The content of an email is received in multiple parts called data fragments.

If you are attempting the stretch goal:

- Once you have the packets you want showing on your packet list in Wireshark (the main screen), go to **File -> Export Objects -> IMF...**
- Now you can save a specific packet as a `.eml` file (format for saving email messages).
- Open the file using an email client (Mail, Outlook, etc) and take a screenshot.
- HELP! My antivirus is saying the `.eml` file is a virus!!!

*AI opportunity:* Use AI to understand command line tools → Wireshark filters

## 📬 Submitting Your Project

📄 Project 1 Submission Template (Google Doc)

### ✔ Am I Ready to Submit?

Check if you're ready to submit with the following questions:

- [ ] Did you complete all of the Required Challenges?
- [ ] Did you copy and fill out the Project 1 Submission Template?
  - It is important that you follow the same layout as the Google doc template so that we can easily access your work.
  - Be sure to check off each feature that is implemented in the "Submission Checklist" section
- [ ] Are any required images/GIFs/videos correctly displaying in your document?
- [ ] Did you set your document to "Anyone with the link can Edit"?

If you answered yes to all of these questions, you are ready to submit! Look for the "Submit" button at the top of this page.

## 🔑 Key Takeaways

- BEC works because phishing emails are designed to look legitimate — the attack lives in the metadata (sending IP, SMTP headers, routing path), not in obvious red flags in the email body.
- Packet captures let you inspect network activity at a level email clients hide from users; the ability to extract and read raw SMTP traffic is a foundational forensic skill.
- The IP-to-email attribution chain you built here is how real analysts trace phishing campaigns back to their infrastructure, even when attackers spoof display names and sender domains.

## 📣 Submissions Policy

- All students are allowed deadline extensions of up to 48 hours on assignments.
- Students do not need to submit a request to use these extensions; they will be automatically applied.
- Students must submit all assignments before the deadline or deadline extension in order to stay actively enrolled in the course.
- Students are not allowed to have any missing assignments at any point during the course.
