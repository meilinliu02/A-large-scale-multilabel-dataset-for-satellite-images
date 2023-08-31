import random
import urllib.request
from shapely.geometry import shape, Point
from skimage.exposure import rescale_intensity
import numpy as np
import ee
import argparse
import csv
import json
from multiprocessing.dummy import Pool, Lock
import os
from os.path import join, isdir, isfile
from os import mkdir, listdir
from collections import OrderedDict
import time
from datetime import datetime, timedelta
import warnings
warnings.simplefilter('ignore', UserWarning)
from tqdm import tqdm


class GeoSampler:

    def sample_point(self):
        raise NotImplementedError()


class NAIPSampler(GeoSampler):
    def __init__(self, rows):
        self.rows = rows
        self.fnames = [tmp[-1] for tmp in rows]

    def sample_point(self, idx):
        row = [self.fnames[idx], (float(self.rows[idx][3]), float(
            self.rows[idx][4])), '2008-01-01', '2023-02-14']
        return row

    def __iter__(self):
        return iter(self.fnames)

    def __len__(self):
        return len(self.fnames)

    @staticmethod
    def km2deg(kms, radius=6371):
        return kms / (2.0 * radius * np.pi / 360.0)


def get_collection():
    collection = ee.ImageCollection('USDA/NAIP/DOQQ')
    return collection


def filter_collection(collection, coords, period=None, halfwidth=0.005):
    print("filtering collection")
    # Calculate the bounding box coordinates
    min_lon = coords[0] - halfwidth
    max_lon = coords[0] + halfwidth
    min_lat = coords[1] - halfwidth
    max_lat = coords[1] + halfwidth

    # Create a bounding box geometry
    bounding_box = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    # Start with the initial collection
    filtered = collection

    if period is not None:
        filtered = filtered.filterDate(*period)  # filter time

    # Apply the bounding box filter
    filtered = filtered.filterBounds(bounding_box)

    size_of = filtered.size().getInfo()

    if size_of == 0:
        print("filtered size is 0")
        raise ee.EEException(
            f'ImageCollection.filter: No suitable images found in ({coords[1]:.4f}, {coords[0]:.4f}) between {period[0]} and {period[1]}.')
    return filtered,size_of


# def filter_collection(collection, coords, period=None, halfwidth=0.005):
#     filtered = collection
#     if period is not None:
#         filtered = filtered.filterDate(*period)  # filter time
#     filtered = filtered.filterBounds(ee.Geometry.Point(
#         [coords[0]-halfwidth, coords[1]-halfwidth]))  # filter region
#     filtered = filtered.filterBounds(ee.Geometry.Point(
#         [coords[0]-halfwidth, coords[1]+halfwidth]))  # filter region
#     filtered = filtered.filterBounds(ee.Geometry.Point(
#         [coords[0]+halfwidth, coords[1]-halfwidth]))  # filter region
#     filtered = filtered.filterBounds(ee.Geometry.Point(
#         [coords[0]+halfwidth, coords[1]+halfwidth]))  # filter region
#     if filtered.size().getInfo() == 0:
#         print("filtered size is 0")
#         raise ee.EEException(
#             f'ImageCollection.filter: No suitable images found in ({coords[1]:.4f}, {coords[0]:.4f}) between {period[0]} and {period[1]}.')
#     return filtered

# def get_patch(collection, coords, bands=None, scale=None, save_path=None, fname=None):
#     if isfile(join(save_path, fname.split('/')[-1])):
#         return None
    
#     if bands is None:
#         bands = RGB_BANDS
    
#     # Sort the collection by time in descending order
#     collection = collection.sort('system:time_start', False)
    
#     # Define the bounding box region
#     min_lon = coords[0] - halfwidth
#     max_lon = coords[0] + halfwidth
#     min_lat = coords[1] - halfwidth
#     max_lat = coords[1] + halfwidth
#     region = ee.Geometry.Rectangle([[min_lon, min_lat], [max_lon, max_lat]])
    
#     # Get the image list from the collection
#     image_list = collection.toList(collection.size())
    
#     try:
#         # Iterate through the images
#         for ind in range(image_list.size().getInfo()):
#             image = ee.Image(image_list.get(ind))
#             image_info = image.getInfo()
            
#             timestamp = image_info['properties']['system:index']
#             patch = image.select(*bands)
            
#             # Generate URL for thumbnail
#             url = patch.getThumbURL({
#                 'bands': bands,
#                 'scale': scale or 1,
#                 'format': 'jpg',
#                 'crs': 'EPSG:4326',
#                 'region': region,
#                 'min': 0,
#                 'max': 255
#             })
            
#             # Download and save the image
#             urllib.request.urlretrieve(url, join(save_path, fname.split('/')[-1]))
            
#             # Break after processing the first image
#             break
#     except Exception as e:
#         print(f"Error: {e}")
    
#     return None


def get_patch(collection, coords, size_of, bands=None, scale=None, save_path=None, fname=None):
    print("entered get_patch")
    if isfile(join(save_path, fname.split('/')[-1])):
        print("file exists")
        return None
    if bands is None:
        bands = RGB_BANDS
    collection = collection.sort('system:time_start', False)
    # print("sorted collection")
    # print("the image should appear")
    # thanks to shitty ee api
    # size_of = collection.size().getInfo()
    # print("size of collection",size_of)
    collection = collection.toList(collection.size())
    # print('reached to list')
    halfwidth = 0.0012
    # region = ee.Geometry.Rectangle(
    #     [[coords[1]-halfwidth,coords[0]-halfwidth], [coords[1]+halfwidth,coords[0]+halfwidth]])
    # Define the bounding box region
    min_lon = coords[0] - halfwidth
    max_lon = coords[0] + halfwidth
    min_lat = coords[1] - halfwidth
    max_lat = coords[1] + halfwidth
    region = ee.Geometry.Rectangle([[min_lon, min_lat], [max_lon, max_lat]])
    #  print region coordinates
    print("region",(min_lon, min_lat, max_lon, max_lat))
    print("reached region")

    # print region
    for ind in range(size_of):
        print("entered for loop")
        try: 
            patch = ee.Image(collection.get(ind)).select(*bands)
            print("patch made")
            print("bands",bands)
            exit()
            url1 = patch.getDownloadURL({'bands': bands,'scale': 1, 'format': 'GEO_TIFF', 'crs':'EPSG:4326', 'region': region, 'min': 0, 'max': 255, 'gamma': 1.0})
            # urllib.request.urlretrieve(url, join(save_path, fname.split('/')[-1].split('.')[0]+'.tiff'))
            print("url1",url1)
            url = patch.getThumbURL({'bands': bands, 'scale': 150, 'format': 'jpg',
                                'crs': 'EPSG:4326', 'region': region, 'min': 0, 'max': 255})
            # print url
            print("URL",url)
            try:
                urllib.request.urlretrieve(url, join(save_path, fname.split('/')[-1]))
            except Exception as e:
                continue
            print("Image downloaded")
            break
        except Exception as e:
            print("error processing image at index",ind)
            continue
    return None


def date2str(date):
    return date.strftime('%Y-%m-%d')


def get_period(date, days=10):
    date1 = date[0] - timedelta(days=days)
    date2 = date[1] + timedelta(days=days)
    return date1, date2


def get_patches(collection, coords, startdate, enddate, debug=False, halfwidth=0.005, **kwargs):
    print("starting to get patches")
    period = (startdate, enddate)
    try:
        filtered_collection,size_of = filter_collection(
            collection, coords, period, halfwidth=halfwidth)
        print("filtered collection")
        patches = get_patch(filtered_collection, coords,size_of, **kwargs)
    except Exception as e:
        if debug:
            print(e)
        # raise
        return None
    return patches


class Counter:
    def __init__(self, start=0):
        self.value = start
        self.lock = Lock()

    def update(self, delta=1):
        with self.lock:
            self.value += delta
            return self.value
        




if __name__ == '__main__':
    b4 = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument('--which', type=str, default="NAIP",
                        choices=['NAIP', 'Sentinel-2', 'Sentinel-2-Temporal'])
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--num_workers', type=int, default=32)
    parser.add_argument('--cloud_pct', type=int, default=10)
    parser.add_argument('--log_freq', type=int, default=100)
    parser.add_argument('--indices_file', type=str, default=None)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    ee.Initialize()
    collection = get_collection()

    scale = {'B1': 60, 'B2': 10, 'B3': 10, 'B4': 10, 'B5': 20, 'B6': 20,
             'B7': 20, 'B8': 10, 'B8A': 20, 'B9': 60, 'B11': 20, 'B12': 20}
    RGB_BANDS = ['B4', 'B3', 'B2']
    if args.which == "NAIP":
        Sampler = NAIPSampler
        save_path = 'images'
        scale = {'R': 1, 'G': 1, 'B': 1}
        RGB_BANDS = ['R', 'G', 'B']
        halfwidth = 0.0012

    if not isdir(save_path):
        mkdir(save_path)

    counter = Counter()
    print(time.time()-b4)


    idir='coords'
    files = sorted(listdir(idir))
    random.shuffle(files)
    cutoff = 0
    for file in files:
        if 'tennis' in file:
            cutoff = 100/(11000*11000)
        if 'swimming_pool' in file:
            cutoff = 100/(11000*11000)
        if 'roundabout' in file:
            cutoff = 400/(11000*11000)
        if 'runway' in file:
            cutoff = 100/(11000*11000)
        if not isdir(join(save_path, file.split('.')[0])):
            mkdir(join(save_path, file.split('.')[0]))
        rows = []
        with open(join(idir, file),encoding='cp1252') as ifd:
            reader = csv.reader(ifd, delimiter=',')
            for i, row in enumerate(reader):
                if row!=[]:
                    # print(i)
                    # print(file)
                    halfwidth=float(row[0])**(.5)
                    if float(row[0]) > cutoff:
                        rows.append([None, None, None, float(row[2]), float(row[1]), '_'.join(
                            [str(i).zfill(5)]+[str(np.round(float(tmp), 6)) for tmp in row[1:3]]+[str(int(np.round(float(tmp), 6))) for tmp in row[3:]])+'.jpg'])
        sampler = Sampler(rows)

        def worker(idx):
            pts = sampler.sample_point(idx)
            patches = get_patches(collection, pts[1], pts[2], pts[3], bands=RGB_BANDS, scale=scale, debug=args.debug, save_path=join(save_path, file.split('.')[0]), fname=pts[0], halfwidth=halfwidth)
            return

        print(file, len(sampler))
        indices = range(len(sampler))
        \
        for i in tqdm(range(2)):
            # print(i)
            worker(i)
        exit()

        if args.num_workers == 0:
            print("starting")
            exit()
            for i in tqdm(range(len(sampler))):

                print(i)
                # worker(i)
                exit()

            # for i in tqdm(indices):
            #     worker(i)
            #     # break
            print("completed")
        # else:
        #     with Pool(args.num_workers) as p:
        #         p.map(worker, indices)