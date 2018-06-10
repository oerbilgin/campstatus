"""Functions to analyze campground and trailhead data
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import geopy.distance

def mean_of_mean_distance_to_centroid(kmeans_data, X):
	"""Calculates all of the mean of mean distances to a centroid.

	Within a group, the mean distance from point to centroid is
	calculated. These within-group means are then averaged for a given
	kmeans solution and collected into a list that is returned.
	
	Args:
	    kmeans_data (list(sklearn.cluster.KMeans)): list of results of KMeans 
	        algorithm performed with different k
	    X (numpy.array): Input to KMeans algorithm
	
	Returns:
	    list: List of mean of mean distances to centroid for each k
	
	"""
	all_mean_distances = []
	for clst in kmeans_data:
	    ssd_collect = []
	    mean_distance_collect = []
	    for i, centroid in enumerate(clst.cluster_centers_):
	        points = pd.np.argwhere(clst.labels_ == i).flatten()
	        ssd = 0
	        distances = 0
	        for idx in points:
	            p = X[idx]
	            dist = geopy.distance.vincenty(centroid, p).km
	            distances += dist
	        # this is kind of like a rough "radius" of distance around the centroid
	        mean_distance = distances / len(points)
	        mean_distance_collect.append(mean_distance)
	    mean_mean_distance = pd.np.asarray(mean_distance_collect).mean()
	    all_mean_distances.append(mean_mean_distance)
	return all_mean_distances

def group_points(
	df,
	n_iters=250,
	ub_in_clust=20,
	lb_in_clust=2,
	max_radius=2.5,):
	"""Groups point in a dataset together by geography.
	
	Uses k-means algorithm to group points together. Selects
	best number of clusters based on the mean distance from each point
	to the centroid. For a given k, the average distance to centroid is
	calculated for each point in the cluster, and those mean distances
	are also averaged. The k yielding the closest mean distance to
	2.5 kilometers, but is less than 2.5 kilometers, is selected as
	the "best" k.
	
	This can be used as a pandas groupby function.
	
	Args:
	    df (pandas.DataFrame): Table containing latitude and longitude
	    	information for each point. These are the points to be merged
	    n_iters (int, optional): number of iterations for KMeans.
	        Equivalent to n_init in sklearn.cluster.KMeans
	    ub_in_clust (int, optional): Rough upper limit of number of
	        points in a cluster.
	    lb_in_clust (int, optional): Rough lower limit of number of
	        points in a cluster
	    max_radius (float, optional): Rough upper limit of the average
	        distance from a given point to its group's centroid.
	
	Returns:
	    pandas.DataFrame: Input dataframe with an additional column named
	        'Geo Group' that represents what kmeans group that point
	        belongs to
	
	"""

	# get clean values (no NaN)
	clean = df[['Latitude', 'Longitude']].dropna()
	X = clean.values

	# calculate lower and upper cluster sizes
	# want fewer than ~20 points in a cluster
	lower_k = len(X) // ub_in_clust
	# want more than ~2 points in a cluster
	upper_k = len(X) // lb_in_clust

	# calculate clusters for each k in the range
	kmeans_data = []
	r = range(lower_k,upper_k)
	for k in r:
	    clst = KMeans(k, n_jobs=-1, n_init=n_iters).fit(X)
	    kmeans_data.append(clst)

	# calculate the mean of mean distances to centroid
	all_mean_distances = mean_of_mean_distance_to_centroid(kmeans_data, X)

	# get the number of clusters to make the mean "radius" of a cluster close to 2.5
	# the average longest distance between two points will be 5 km
	m = pd.np.asarray(all_mean_distances)
	try:
		best_k = pd.np.argwhere(m <= 2.5).flatten()[0]
	except IndexError as e:
		best_k = -1
		print 'Warning: best_k\'s radius is {} for {}, higher than desired 2.5'.format(
			m[best_k],
			df['Forest'].iloc[0]
			)

	best_cluster = kmeans_data[best_k]

	df.loc[clean.index, 'Geo Group'] = best_cluster.labels_

	return df
