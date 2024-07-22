# Use a Python base image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code file
COPY . .

# Expose the port Flask is running on
EXPOSE 3000

# Command to run when starting the container
CMD ["python", "-u", "discord_bot.py"]