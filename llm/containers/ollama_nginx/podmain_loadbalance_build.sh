#####
#####
###     Create a podman network
#######  podman network create ollama-net
#### then
# podman run -d \
#  --name ollama-1 \
#  --network ollama-net \
#  ollama/ollama

# podman run -d \
#  --name ollama-2 \
#  --network ollama-net \
#  ollama/ollama
#
# then build using this:
#
#
# And when you run the nginx
# podman run -d \
#  --name ollama-proxy \
#  --network ollama-net \
#  -p 8080:8080 \
#  nginx-ollama-proxy


events {}

http {
    upstream ollama_backend {
        least_conn;   # or round-robin (default)

        server ollama-1:11434;
        server ollama-2:11434;
    }

    server {
        listen 8080;

        location /api/ {
            proxy_pass http://ollama_backend/api/;
            proxy_http_version 1.1;

            proxy_set_header Host $host;
            proxy_set_header Connection "";
            proxy_buffering off;

            # Important for long generations
            proxy_read_timeout 3600s;
        }
    }
}

