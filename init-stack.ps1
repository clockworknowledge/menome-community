# Initialize Neo4j and MinIO buckets
Write-Output "Initializing Neo4j and MinIO buckets..."
docker compose exec -T api-dev python /menome/init_stack.py @args
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to initialize Neo4j and MinIO buckets."
    exit $LASTEXITCODE
}

# Set up MinIO access
Write-Output "Setting up MinIO access..."

# Load environment variables from .env file if it exists
$envFile = ".env"
if (Test-Path $envFile) {
    Write-Output "Loading environment variables from $envFile..."
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        # Skip empty lines and comments
        if ($line -and -not $line.StartsWith('#')) {
            $parts = $line -split '=', 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim().Trim('"').Trim("'")
                # Check if key matches the regex ^[A-Za-z_][A-Za-z0-9_]*$
                if ($key -match '^[A-Za-z_][A-Za-z0-9_]*$') {
                    Write-Output "Setting environment variable: $key = $value"
                    try {
                        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                    }
                    catch {
                        Write-Error "Failed to set environment variable: $key"
                    }
                }
                else {
                    Write-Warning "Invalid environment variable name: $key. Skipping."
                }
            }
            else {
                Write-Warning "Invalid line in .env file: $_. Skipping."
            }
        }
    }
}
else {
    Write-Warning ".env file not found. Proceeding without loading environment variables."
}

# Configuration from .env file
$MINIO_ALIAS = "minio-dev"
$MINIO_CONTAINER = "minio-dev"

# Handle MINIO_SECURE to determine protocol
if ($env:MINIO_SECURE -eq "True") {
    $protocol = "https://"
}
else {
    $protocol = "http://"
}

$MINIO_ENDPOINT = if ($env:MINIO_ENDPOINT) { 
    # Ensure the endpoint starts with http:// or https://
    if ($env:MINIO_ENDPOINT -notmatch '^https?://') {
        "$protocol$($env:MINIO_ENDPOINT)"
    }
    else {
        $env:MINIO_ENDPOINT
    }
} else { 
    "http://localhost:9000" 
}

$ROOT_ACCESS_KEY = $env:MINIO_ROOT_USER
$ROOT_SECRET_KEY = $env:MINIO_ROOT_PASSWORD
$NEW_ACCESS_KEY = $env:MINIO_ACCESS_KEY
$NEW_SECRET_KEY = $env:MINIO_SECRET_KEY
$USER_POLICY = if ($env:USER_POLICY) { $env:USER_POLICY } else { "readwrite" }

# Debugging: Output configuration variables
Write-Output "Configuration Variables:"
Write-Output "MINIO_ALIAS: $MINIO_ALIAS"
Write-Output "MINIO_CONTAINER: $MINIO_CONTAINER"
Write-Output "MINIO_ENDPOINT: $MINIO_ENDPOINT"
Write-Output "ROOT_ACCESS_KEY: $ROOT_ACCESS_KEY"
Write-Output "ROOT_SECRET_KEY: $ROOT_SECRET_KEY"
Write-Output "NEW_ACCESS_KEY: $NEW_ACCESS_KEY"
Write-Output "NEW_SECRET_KEY: $NEW_SECRET_KEY"
Write-Output "USER_POLICY: $USER_POLICY"

# Check if essential variables are set
if (-not $ROOT_ACCESS_KEY) {
    Write-Error "MINIO_ROOT_USER is not set. Please check your .env file."
    exit 1
}
if (-not $ROOT_SECRET_KEY) {
    Write-Error "MINIO_ROOT_PASSWORD is not set. Please check your .env file."
    exit 1
}
if (-not $NEW_ACCESS_KEY) {
    Write-Error "MINIO_ACCESS_KEY is not set. Please check your .env file."
    exit 1
}
if (-not $NEW_SECRET_KEY) {
    Write-Error "MINIO_SECRET_KEY is not set. Please check your .env file."
    exit 1
}

# Check if mc is already configured for the alias
Write-Output "Checking if mc alias '$MINIO_ALIAS' is already configured..."
$mcAliasList = docker exec $MINIO_CONTAINER mc alias list 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to list mc aliases: $mcAliasList"
    exit $LASTEXITCODE
}

if ($mcAliasList -notmatch $MINIO_ALIAS) {
    # Configure mc alias for MinIO server
    Write-Output "Configuring mc alias for MinIO..."
    $mcSetOutput = docker exec $MINIO_CONTAINER mc alias set $MINIO_ALIAS $MINIO_ENDPOINT $ROOT_ACCESS_KEY $ROOT_SECRET_KEY 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Configured mc alias for MinIO."
    }
    else {
        Write-Error "Failed to configure mc alias for MinIO. Error: $mcSetOutput"
        exit $LASTEXITCODE
    }
}
else {
    Write-Output "mc alias already configured for MinIO."
}

# Create the new user
Write-Output "Creating new MinIO user with access key: $NEW_ACCESS_KEY..."
$mcUserAddOutput = docker exec $MINIO_CONTAINER mc admin user add $MINIO_ALIAS $NEW_ACCESS_KEY $NEW_SECRET_KEY 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Output "Created new user with access key: $NEW_ACCESS_KEY"
}
else {
    Write-Error "Failed to create new user with access key: $NEW_ACCESS_KEY. Error: $mcUserAddOutput"
    # Optionally, exit or continue based on your requirements
}

# Attach policy to the user
Write-Output "Attaching policy '$USER_POLICY' to user: $NEW_ACCESS_KEY..."
$mcPolicyAttachOutput = docker exec $MINIO_CONTAINER mc admin policy attach $MINIO_ALIAS $USER_POLICY --user $NEW_ACCESS_KEY 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Output "Policy '$USER_POLICY' applied to user: $NEW_ACCESS_KEY"
}
else {
    Write-Error "Failed to apply policy '$USER_POLICY' to user: $NEW_ACCESS_KEY. Error: $mcPolicyAttachOutput"
    # Optionally, exit or continue based on your requirements
}

# Create necessary buckets
$notesBucket = "$MINIO_ALIAS/notes"
$filesBucket = "$MINIO_ALIAS/files"

# Function to create a bucket if it doesn't exist
function Create-Bucket {
    param (
        [string]$BucketName
    )

    Write-Output "Creating or verifying bucket: $BucketName..."
    $result = docker exec $MINIO_CONTAINER mc mb $BucketName 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ($result -match "Bucket '.*' already exists") {
            Write-Output "Bucket '$($BucketName.Split('/')[-1])' already exists."
        }
        else {
            Write-Error "Failed to create bucket '$BucketName': $result"
        }
    }
    else {
        Write-Output "Created bucket '$($BucketName.Split('/')[-1])'."
    }
}

# Create or verify the 'notes' bucket
Create-Bucket -BucketName $notesBucket

# Create or verify the 'files' bucket
Create-Bucket -BucketName $filesBucket

Write-Output "Created or verified buckets 'notes' and 'files'."

# Exit with the last exit code
exit $LASTEXITCODE
