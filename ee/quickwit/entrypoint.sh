#!/bin/sh

# This script will rplace the env variable values to the config files

ls config/
find /quickwit/ -type f -name "*.yaml" -exec sed -i "s#{{KAFKA_SERVER}}#${KAFKA_SERVER}#g" {} \;
find /quickwit/ -type f -name "*.yaml" -exec sed -i "s#{{AWS_BUCKET}}#${AWS_BUCKET}#g" {} \;
find /quickwit/ -type f -name "*.yaml" -exec sed -i "s/{{QUICKWIT_TOPIC}}/${QUICKWIT_TOPIC}/g" {} \;
find /quickwit/ -type f -name "*.yaml" -exec sed -i "s/{{QUICKWIT_PORT}}/${QUICKWIT_PORT}/g" {} \;
find /quickwit/ -type f -name "*.yaml" -exec sed -i "s#{{data_dir_path}}#${data_dir_path}#g" {} \;

./quickwit_start_task.sh & pid1=$!
sleep 120
echo "Creating indexes.."
quickwit index create --index-config index-config-fetch.yaml
quickwit index create --index-config index-config-graphql.yaml
quickwit index create --index-config index-config-pageevent.yaml
echo "Running kafka reader.."
python3 -u consumer.py & pid2=$!
wait $pid1 $pid2

