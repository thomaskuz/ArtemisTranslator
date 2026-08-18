# NodeRed with AMQP Support for linux/amd64
# This Dockerfile creates a NodeRed image with the @meowwolf/node-red-contrib-amqp
# package pre-installed for deployment to offline Kubernetes environments

# NodeRed base image
FROM nodered/node-red:latest

# Switch to root user to install npm packages
USER root

# Install the AMQP node for NodeRed globally
# This makes the @meowwolf/node-red-contrib-amqp package available without internet
RUN npm install -g @meowwolf/node-red-contrib-amqp

# Verify installation was successful
RUN npm list -g @meowwolf/node-red-contrib-amqp

# Switch back to node-red user (non-root for security)
USER node-red

# Expose NodeRed web interface port
EXPOSE 1880

# Default command
CMD ["node-red"]
