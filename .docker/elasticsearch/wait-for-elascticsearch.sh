#!/bin/bash

if [ "$SEARCH_ENGINE" = "elasticsearch" ]
then
    echo "Waiting for elasticsearch..."
    
    while ! nc -z "wuloevents.elasticsearch" $ELASTICSEARCH_DSL_PORT; do
      echo $ELASTICSEARCH_DSL_HOST
      echo $ELASTICSEARCH_DSL_PORT
      sleep 0.7
    done

    echo "Elastic search started"
fi