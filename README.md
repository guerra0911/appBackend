# Django Application Deployment Guide

This guide outlines the steps to update your Django application hosted on an AWS EC2 instance after making changes on your local machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Machine Changes](#local-machine-changes)
3. [Deploying to EC2](#deploying-to-ec2)
4. [Managing Gunicorn Service](#managing-gunicorn-service)
5. [Monitoring and Logs](#monitoring-and-logs)

## Prerequisites

- Ensure you have SSH access to your EC2 instance.
- Your project is set up with a virtual environment.
- Gunicorn and Nginx are configured on your EC2 instance.

## Local Machine Changes

1. **Make Changes to Your Code**:
   - Edit files, add new features, fix bugs, etc.

2. **Commit and Push Changes to GitHub**:
   ```sh
   git add .
   git commit -m "Describe your changes"
   git push origin master

3. **SSH into EC2 Instance**
    - $ cd C:/Users/Nicholas/ssh_keys/
    - $ ssh -i mobileappkeypair.pem ubuntu@ec2-18-119-118-178.us-east-2.compute.amazonaws.com
    
4. **Pull Changes**
    - cd /home/ubuntu/appBackend
    - git pull origin master
    - source venv/bin/activate
    - pip install -r requirements.txt
    - python manage.py migrate

5. **Restart Gunicorn**
    - sudo systemctl restart gunicorn
    - sudo systemctl status gunicorn


## Checking Server Logs
1. **Gunicorn Logs**
    - sudo journalctl -u gunicorn

2. **Nginx Logs**
    - sudo tail -f /var/log/nginx/access.log
    - sudo tail -f /var/log/nginx/error.log

