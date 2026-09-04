# Deploy to another static host

The extracted `public/` directory is the website root. Configure the selected
service to serve `public/index.html` at the site's main URL and copy the complete
directory without changing its paths.

Common hosting options include:

- A generic static server can serve `public/` directly. For a local check, run
  `python3 -m http.server --directory public 8000` and open
  `http://localhost:8000`.
- For Apache HTTP Server, copy the contents of `public/` to the configured
  `DocumentRoot`. See [Getting Started with Apache](https://httpd.apache.org/docs/current/en/getting-started.html).
- For NGINX, set the server `root` to the extracted `public/` directory. See the
  [NGINX Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html).
- For Google Cloud Storage, upload the contents of `public/` to a bucket configured
  for website hosting. See [Hosting a static website](https://docs.cloud.google.com/storage/docs/hosting-static-website).

After deployment, confirm the home page loads with styling and that at least one
skill ZIP can be downloaded.
