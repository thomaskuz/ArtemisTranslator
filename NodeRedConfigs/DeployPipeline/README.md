# NodeRed Export Pipeline for Kubernetes

This folder contains the Dockerfile and export script for building a custom NodeRed image with AMQP support and exporting it for offline Kubernetes deployment.

## Quick Start

**When you're ready to deploy to Kubernetes, run:**

```bash
./export.sh
```

This creates `nodered-with-amqp.tar` that you can transfer to your Kubernetes environment.

## Understanding the Pipeline

### Local Development (Before Export)

Use the standard setup for development:

```bash
# From project root
docker-compose up -d

# Develop your flows at http://localhost:1880
```

**No special setup needed** — NodeRed works normally.

### Export Pipeline (When Ready to Deploy)

When you're ready to deploy to Kubernetes:

```bash
# From this folder (NodeRedConfigs/DeployPipeline)
./export.sh
```

This:
1. **Builds** NodeRed image for amd64 with AMQP pre-installed
2. **Verifies** AMQP package is included
3. **Exports** image as tar file for transfer
4. **Shows** next steps for Kubernetes deployment

## Files in This Folder

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds NodeRed with @meowwolf AMQP package for amd64 |
| `export.sh` | Automates build, verify, and export process |
| `README.md` | This file |

## Prerequisites

✅ Docker installed on your Mac
✅ `docker buildx` installed (check: `docker buildx version`)
✅ Access to your Kubernetes environment

## Step-by-Step Guide

### Step 1: Develop Your Flows Locally

```bash
cd /path/to/ArtemisTranslator

# Start normal development
docker-compose up -d

# Create and test your flows at http://localhost:1880
# Flows are persistent in the nodered_data volume
```

### Step 2: Export When Ready

```bash
# Stop local development (optional)
docker-compose down

# Navigate to this folder
cd NodeRedConfigs/DeployPipeline

# Run export script
./export.sh
```

Output will show:
```
[1/4] Building NodeRed image for amd64 architecture...
[2/4] Verifying AMQP package installation...
[3/4] Exporting image to tar file...
[4/4] Preparing for transfer...

File location: ./nodered-with-amqp.tar
File size: 512M
```

### Step 3: Transfer to Kubernetes

Copy the tar file to your Kubernetes environment:

```bash
# From this folder
scp nodered-with-amqp.tar user@kubernetes-server:/path/to/images/
```

Or use USB, network share, cloud storage, etc.

### Step 4: Load on Kubernetes Machine

On the Kubernetes machine (amd64 Linux):

```bash
# Load the image
docker load -i nodered-with-amqp.tar

# Verify it loaded
docker images | grep nodered-with-amqp
```

You should see:
```
nodered-with-amqp   latest   <image-id>   512M
```

### Step 5: Deploy on Kubernetes

Use the standard docker-compose.yml:

```bash
# Copy docker-compose.yml to Kubernetes machine
scp ../../docker-compose.yml user@kubernetes-server:/path/to/

# Deploy
docker-compose up -d
```

Your flows are persistent! They're stored in the `nodered_data` volume created during export.

## What's Included in the Export

The `nodered-with-amqp.tar` file contains:

✅ NodeRed v4.x
✅ @meowwolf/node-red-contrib-amqp package
✅ All dependencies
✅ Configured for amd64 (Linux on Kubernetes)
✅ Ready for offline deployment (no internet needed)

## Architecture Details

### Why Two Workflows?

| Local Development | Kubernetes Export |
|---|---|
| `docker-compose up -d` | `./export.sh` |
| Uses: nodered/node-red:latest | Uses: Custom nodered-with-amqp |
| Standard image (flexible) | amd64 image (fixed for Kubernetes) |
| Requires internet (npm install in UI) | No internet needed (AMQP pre-installed) |

### Architecture Compatibility

- **Your Mac**: ARM64 (M4 chip)
- **Kubernetes**: amd64 (Linux)
- **Export Script**: Builds amd64 on your ARM Mac using `docker buildx`
- **Result**: Works perfectly on amd64 Kubernetes

## Troubleshooting

### "export.sh: permission denied"

Make it executable:
```bash
chmod +x export.sh
```

### Script gets stuck on verification

Stop any running containers:
```bash
docker ps | grep nodered
docker stop <container-id>
```

Then try again.

### Tar file not created

Check disk space:
```bash
df -h
# Need at least 1GB free
```

Check permissions:
```bash
ls -la
# Should be able to write to this folder
```

### "Image not found" on Kubernetes

Verify image was loaded:
```bash
docker images | grep nodered
```

If not there, load again:
```bash
docker load -i nodered-with-amqp.tar
```

## File Size

The exported tar file is typically **500MB - 1GB**.

If you need to compress for transfer:

```bash
gzip nodered-with-amqp.tar
# Creates: nodered-with-amqp.tar.gz (~200MB)

# On Kubernetes side, decompress:
tar xzf nodered-with-amqp.tar.gz
docker load -i nodered-with-amqp.tar
```

## Persistence

Your flows are persistent across restarts because:

1. **Local development**: `nodered_data` Docker volume
2. **Kubernetes export**: Volume config in docker-compose.yml
3. **Result**: Flows survive container restarts

Flows stored in: `/data/flows.json` (inside container)

## Customization

### Adding More Packages

Edit `Dockerfile`:

```dockerfile
FROM nodered/node-red:latest
USER root
RUN npm install -g @meowwolf/node-red-contrib-amqp
RUN npm install -g node-red-contrib-your-package  # Add more
USER node-red
```

Then re-run `export.sh`.

### Including Default Flows

Add `flows.json` to this folder, then:

```dockerfile
COPY flows.json /data/flows.json
RUN chown -R node-red:node-red /data
```

## Next Steps

1. ✅ Develop flows locally with `docker-compose up -d`
2. ✅ Run `./export.sh` when ready to deploy
3. ✅ Transfer tar file to Kubernetes
4. ✅ Load and deploy on Kubernetes

Questions? Check the parent project README or CONTRIBUTING.md.
