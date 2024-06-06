FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Update and install necessary packages
RUN apt update && apt upgrade -y
RUN apt install wget unzip zip default-jre cron curl -y -qq

# Download and unzip the client portal gateway
RUN wget https://download2.interactivebrokers.com/portal/clientportal.gw.zip
RUN unzip clientportal.gw.zip

# Copy configuration files and scripts
COPY conf.yaml /app/root/conf.yaml

# Start cron service and execute the main script
CMD bash bin/run.sh root/conf.yaml
