# Use the official Redis image
FROM redis:7-alpine

# Expose default Redis port
EXPOSE 6379

# Start Redis server
CMD ["redis-server", "--save", "60", "1", "--loglevel", "warning"]


COPY redis.conf /usr/local/etc/redis/redis.conf
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

