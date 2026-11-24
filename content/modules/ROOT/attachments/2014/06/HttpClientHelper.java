package com.secodis.example.securitytests;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UnsupportedEncodingException;
import java.net.CookieHandler;
import java.net.CookieManager;
import java.net.URL;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import org.apache.http.Consts;
import org.apache.http.HttpResponse;
import org.apache.http.NameValuePair;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.message.BasicNameValuePair;

public class HttpClientHelper
{
	private HttpClient client = HttpClientBuilder.create().build();
	private final String USER_AGENT = "Mozilla/5.0";

	public HttpResponse sendRequest( String type, URL url, List<NameValuePair> params  ) throws ClientProtocolException, IOException
	{
		CloseableHttpClient client = HttpClientBuilder.create().build();

		if (type == "POST") {
			// send a HTTP POST request
			HttpPost post = new HttpPost(url.toString());
			UrlEncodedFormEntity entity = new UrlEncodedFormEntity(params, Consts.UTF_8);
			post.setEntity(entity);

			post.setHeader("Host", url.getHost());
			post.setHeader("User-Agent", USER_AGENT);
			post.setHeader("Content-Type", "application/x-www-form-urlencoded");

			return client.execute(post);
		} else {
			// send a HTTP GET request
			String fullurl = url.toString();

			for (Iterator it = params.iterator(); it.hasNext();) {
				BasicNameValuePair pair = (BasicNameValuePair) it.next();

				if (fullurl.lastIndexOf("?") >= 0) {
					fullurl = fullurl + "&";
				}
				else {
					fullurl = fullurl + "?";
				}

				fullurl = fullurl + pair.getName() + "=" + pair.getValue();		    
			}
			System.out.println("FULLURL" + ": " + fullurl);
			HttpGet get = new HttpGet(url.toString());
			
			get.setHeader("Host", url.getHost());
			get.setHeader("User-Agent", USER_AGENT);

			return client.execute(get);
		}
	}
}