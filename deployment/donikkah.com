upstream chat_backend {
    server 0.0.0.0:8001;
}

server{
        server_name donikkah.com www.donikkah.com;
        root   /home/ubuntu/deploy/apps/donikkah_frontend/;
        index index.html;

        access_log /home/ubuntu/deploy/logs/nginx-access.log;
        error_log /home/ubuntu/deploy/logs/nginx-error.log;


        #location /api {
        #    try_files $uri @proxy_to_donikkah;
       #}

          location /apis {
            try_files $uri $uri/ @proxy_to_donikkah;
       }

        location /ws/ {
            try_files $uri @proxy_to_ws;
        }

   location /media {
        #autoindex on;
        alias /home/ubuntu/deploy/apps/donikkah/media;
    }


#
#        location / {
#            try_files $uri /index.html;
#        }
location / {
    try_files $uri $uri/ /index.html;
}
client_max_body_size 20M; 


    location @proxy_to_donikkah {
      proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_headers_hash_max_size 512;
      proxy_headers_hash_bucket_size 128;
      proxy_connect_timeout 300s;
      proxy_send_timeout 300;
      proxy_read_timeout 300;
      proxy_redirect off;
      #proxy_pass http://donikkah_backend;
      proxy_pass http://0.0.0.0:8001;
    }

    location @proxy_to_ws {
        proxy_pass http://chat_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    add_header Strict-Transport-Security "max-age=63072000; includeSubdomains; preload";
    #ssl on;
    #ssl_protocols TLSv1.2 TLSv1.3;
   
 



    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/donikkah.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/donikkah.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot




}



server{
    if ($host = www.donikkah.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = donikkah.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot
        server_name www.donikkah.com donikkahh.com;
        listen 80;
    return 301 https://$host$request_uri;


}
server{
    if ($host = donikkah.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


        server_name donikkah.com www.donikkah.com;
    listen 80;
    return 404; # managed by Certbot


}
