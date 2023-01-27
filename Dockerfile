FROM python:3

WORKDIR /opt/KintoUn
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update -y && apt install -y curl unzip
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscli.zip"
RUN unzip awscli.zip && ./aws/install

ENTRYPOINT ["./entrypoint.sh"]