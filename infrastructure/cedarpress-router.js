/* exported handler */
// Exact source for the existing cedarpress-router CloudFront Function.
// Publish only after the app login authority and assets have passed acceptance.
function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;
  var uri = request.uri;
  if (host === "www.cedarpress.ai") {
    var query = [];
    var values = request.querystring || {};
    Object.keys(values).forEach(function (key) {
      var item = values[key];
      var entries = item.multiValue || [item];
      entries.forEach(function (entry) {
        // CloudFront supplies the original percent-encoded query values.
        query.push(key + "=" + entry.value);
      });
    });
    return {
      statusCode: 301,
      statusDescription: "Moved Permanently",
      headers: {
        location: { value: "https://cedarpress.ai" + uri + (query.length ? "?" + query.join("&") : "") },
      },
    };
  }

  // API endpoints must never become the successful static app document.
  // Their own origin/behavior is configured separately from this S3 function.
  if (/^\/(?:api|auth|press)(?:\/|$)/.test(uri) || /^\/me\/?$/.test(uri)) return request;

  if (host === "app.cedarpress.ai") {
    var path = uri.length > 1 && uri.endsWith("/") ? uri.slice(0, -1) : uri;
    var pages = ["/", "/articles", "/data", "/settings", "/methods", "/whats-new", "/priorities", "/record",
      "/tribal-data-request", "/research-access"];
    if (pages.indexOf(path) !== -1 || /^\/entity\/[^/]+$/.test(path) || /^\/articles\/[^/]+$/.test(path)) {
      // package.json copies this app shell before public-page prerendering.
      // S3 serves the existing object with 200; unknown routes keep their 404.
      request.uri = "/404.html";
    }
    return request;
  }

  // Preserve the public site's existing prerendered-page and asset behavior.
  if (uri.endsWith("/")) request.uri = uri + "index.html";
  else if (uri.indexOf(".", uri.lastIndexOf("/")) === -1) request.uri = uri + "/index.html";
  return request;
}
