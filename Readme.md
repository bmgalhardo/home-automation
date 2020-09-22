wget https://github.com/prometheus/node_exporter/releases/download/v1.0.1/node_exporter-1.0.1.linux-amd64.tar.gz
tar xvfz node_exporter-*
cd node_exporter-*.*-amd64
./node_exporter



# Home Cinema

TODO
- plex in heimdall reverse proxy

#0 4 * * * cd /home/bgalhardo/Dockers/home-cinema; docker-compose pull; 
#docker-compose up -d; echo $(date): checking new versions >> updates.log 
