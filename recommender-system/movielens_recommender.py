# -*- coding: utf-8 -*-
"""movielens_recommender.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/github/sayid-alt/mymachine-learning/blob/main/recommender-system/movielens_recommender.ipynb

# **IMPORT LIBRARY**
"""

import numpy as np
import pandas as pd
import collections
from mpl_toolkits.mplot3d import Axes3D
from IPython import display
from matplotlib import pyplot as plt
import sklearn
import sklearn.manifold
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
tf.logging.set_verbosity(tf.logging.ERROR)
import altair as alt
import warnings
warnings.filterwarnings('ignore')

alt.data_transformers.enable('default', max_rows=None)

alt.renderers.enable('mimetype')

alt.renderers.enable('colab')

"""# **DOWNLOAD MOVIELENS DATA**"""

print('Downloading movielens data...')
from urllib.request import urlretrieve
import zipfile

urlretrieve("http://files.grouplens.org/datasets/movielens/ml-100k.zip", 'movielens.zip')
zip_ref = zipfile.ZipFile('movielens.zip', 'r')
zip_ref.extractall()
print('Done.')
print(zip_ref.read('ml-100k/u.info'))

"""# **LOAD DATASETS**"""

users_cols = ['user_id', 'age', 'sex', 'occupation', 'zip_code']
users = pd.read_csv('ml-100k/u.user', sep='|', names=users_cols, encoding='latin-1')

ratings_cols = ['user_id', 'movie_id', 'rating', 'unix_timestamp']
ratings = pd.read_csv('ml-100k/u.data', sep='\t', names=ratings_cols, encoding='latin-1')

genre_cols = [
    "genre_unknown", "Action", "Adventure", "Animation", "Children", "Comedy",
    "Crime", "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror",
    "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"
]

movies_cols = [
    'movie_id', 'title', 'release_date', "video_release_date", "imdb_url"
] + genre_cols

movies = pd.read_csv(
    'ml-100k/u.item', sep='|', names=movies_cols, encoding='latin-1'
)

print('Jumlah data film: ', len(movies.movie_id.unique()))
print('Jumlah data pengunjung: ', len(users.user_id.unique()))
print('Jumlah data penayangan: ', len(ratings.user_id))

users["user_id"] = users["user_id"].apply(lambda x: str(x-1))
movies["movie_id"] = movies["movie_id"].apply(lambda x: str(x-1))
movies["year"] = movies['release_date'].apply(lambda x: str(x).split('-')[-1])
ratings["movie_id"] = ratings["movie_id"].apply(lambda x: str(x-1))
ratings["user_id"] = ratings["user_id"].apply(lambda x: str(x-1))
ratings["rating"] = ratings["rating"].apply(lambda x: float(x))

genre_occurences = movies[genre_cols].sum().to_dict()
genre_occurences

def mark_genres(movies, genres):
  def get_random_genre(gs):
    active = [genre for genre, g in zip(genres, gs) if g==1]
    if len(active) == 0:
      return 'Other'
    return np.random.choice(active)

  def get_all_genres(gs):
    active = [genre for genre, g in zip(genres, gs) if g==1]
    if len(active) == 0:
      return 'Other'
    return '-'.join(active)

  movies['genre'] = [
      get_random_genre(gs) for gs in zip(*[movies[genre] for genre in genres])
  ]
  movies['all_genres'] = [
      get_all_genres(gs) for gs in zip(*[movies[genre] for genre in genres])
  ]

mark_genres(movies, genre_cols)

pd.concat([movies['all_genres'], movies['genre']], axis=1)

movielens = ratings.merge(movies, on='movie_id').merge(users, on='user_id')
movielens.head()

"""# **EXPLORATION**"""

pd.options.display.max_rows=10
pd.options.display.float_format = '{:.3f}'.format

def mask(df, key, function):
  """Returns a filtered dataframe, by applying function to key"""
  return df[function(df[key])]

def flatten_cols(df):
  df.columns = [' '.join(col).strip() for col in df.columns.values]
  return df

pd.DataFrame.mask = mask
pd.DataFrame.flatten_cols = flatten_cols

users.describe(include='all')

# Membuat filter untuk melakukan slicing data.
occupation_filter = alt.selection_multi(fields=["occupation"])
occupation_chart = alt.Chart().mark_bar().encode(
    x="count()",
    y=alt.Y("occupation:N"),
    color=alt.condition(
        occupation_filter,
        alt.Color("occupation:N", scale=alt.Scale(scheme='category20')),
        alt.value("lightgray")),
).properties(width=300, height=300, selection=occupation_filter)

# Fungsi yang dapat membuat histogram dari data yang sudah difilter.
def filtered_hist(field, label, filter):
  base = alt.Chart().mark_bar().encode(
      x=alt.X(field, bin=alt.Bin(maxbins=10), title=label),
      y="count()",
  ).properties(
      width=300,
  )
  return alt.layer(
      base.transform_filter(filter),
      base.encode(color=alt.value('lightgray'), opacity=alt.value(.7)),
  ).resolve_scale(y='independent')

users_ratings = (
    ratings
    .groupby('user_id', as_index=False)
    .agg({'rating' : ['count', 'mean']})
    .flatten_cols()
    .merge(users, on='user_id')
)

# Membuat visualisasi atau chart berdasarkan jumlah rating dan rata-rata
alt.hconcat(
    filtered_hist('rating count', '# ratings / user', occupation_filter),
    filtered_hist('rating mean', 'mean user rating', occupation_filter),
    occupation_chart,
    data=users_ratings
)

movies_ratings = movies.merge(
    ratings
    .groupby('movie_id', as_index=False)
    .agg({'rating': ['count', 'mean']})
    .flatten_cols(),
    on='movie_id')

genre_filter = alt.selection_multi(fields=['genre'])
genre_chart = alt.Chart().mark_bar().encode(
    x="count()",
    y=alt.Y('genre'),
    color=alt.condition(
        genre_filter,
        alt.Color("genre:N"),
        alt.value('lightgray'))
).properties(height=300, selection=genre_filter)

# Menampilkan visualisasi
alt.hconcat(
    filtered_hist('rating count', '# ratings / movie', genre_filter),
    filtered_hist('rating mean', 'mean movie rating', genre_filter),
    genre_chart,
    data=movies_ratings)

(movies_ratings[['title', 'rating count', 'rating mean']]
 .mask('rating count', lambda x : x > 20)
 .sort_values(by='rating mean', ascending=True)
 .head(10)
 )

"""# **RECOMMENDER**

<img src="https://dicoding-web-img.sgp1.cdn.digitaloceanspaces.com/original/academy/dos-c556df464b8f49a1a013f375aa9bf28220240625164230.jpeg" />
"""

def split_dataframe(df, holdout_fraction=0.1):
  test = df.sample(frac=holdout_fraction, replace=False)
  train = df[~df.index.isin(test.index)]

  return train, test

ratings[['user_id', 'movie_id']].values

def build_rating_sparse_tensor(ratings_df):
  indices = ratings_df[['user_id', 'movie_id']].values
  values = ratings_df['rating'].values

  return tf.SparseTensor(
      indices=indices,
      values=values,
      dense_shape=(users.shape[0], movies.shape[0])
  )

with tf.Session() as saas:
  print(build_rating_sparse_tensor(ratings).eval())

def sparse_mean_square_error(sparse_ratings, user_embeddings, movie_embeddings):

  # slicing the result of matmul as indices frpm non-null values of sparse_ratings
  predictions = tf.gather_nd(
      # calculate the matrix multipication for users and movies
      tf.matmul(user_embeddings, movie_embeddings,  transpose_b=True),
      indices=sparse_ratings.indices
  )

  # calculate loss
  loss = tf.losses.mean_squared_error(sparse_ratings.values,predictions)

  return loss

class CFModel(object):
  def __init__(self, embedding_vars, loss, metrics=None):
    self._embedding_vars=embedding_vars
    self._loss=loss
    self._metrics=metrics
    self._embeddings={k : None for k in embedding_vars}
    self._session=None

  @property
  def embeddings(self):
    return self._embeddings


  def train(self, num_iterations=100, learning_rate=1.0,
            plot_results=True,
            optimizer=tf.train.GradientDescentOptimizer):

    with self._loss.graph.as_default():
      opt = optimizer(learning_rate)
      train_op = opt.minimize(self._loss)
      local_init_op = tf.group(
          tf.variables_initializer(opt.variables()),
          tf.local_variables_initializer()
      )

      if self._session is None:
        self._session = tf.Session()
        with self._session.as_default():
          self._session.run(tf.global_variables_initializer())
          self._session.run(tf.tables_initializer())
          tf.train.start_queue_runners()

    with self._session.as_default():
      local_init_op.run()
      iterations = []
      metrics = self._metrics or ({},)
      metrics_vals = [collections.defaultdict(list) for _ in self._metrics]

      for i in range(num_iterations + 1):
        _, results = self._session.run((train_op, metrics))
        if (i % 10 == 0) or i == num_iterations:
          print("\r iteration %d: " % i + ", ".join(
              ["%s=%f" % (k, v) for r in results for k, v in r.items()]),
                end='')

          iterations.append(i)
          for matric_val, result in zip(metrics_vals, results):
            for k, v in result.items():
              matric_val[k].append(v)

      for k, v in self._embedding_vars.items():
        self.embeddings[k] = v.eval()

      if plot_results:
        num_subplots = len(metrics)+1
        fig = plt.figure()
        fig.set_size_inches(num_subplots*10, 8)
        for i, metric_vals in enumerate(metrics_vals):
          ax = fig.add_subplot(1, num_subplots, i+1)
          for k, v in metric_vals.items():
            ax.plot(iterations, v, label=k)
          ax.set_xlim([1, num_iterations])
          ax.legend()

      return results

def build_model(ratings, embedding_dims, init_stddev):
  train_ratings, test_ratings = split_dataframe(ratings)
  A_train = build_rating_sparse_tensor(train_ratings)
  A_test = build_rating_sparse_tensor(test_ratings)

  U = tf.Variable(tf.random_normal(
      [A_train.dense_shape[0], embedding_dims], stddev=init_stddev))
  M = tf.Variable(tf.random_normal(
      [A_train.dense_shape[1], embedding_dims], stddev=init_stddev))

  train_loss = sparse_mean_square_error(A_train, U, M)
  test_loss = sparse_mean_square_error(A_test, U, M)

  metrics = {
      'train_error' : train_loss,
      'test_error' : test_loss
  }

  embeddings = {
      'user_id' : U,
      'movie_id' : M
  }

  return CFModel(embeddings, train_loss, metrics=[metrics])

model = build_model(ratings, embedding_dims=30, init_stddev=0.5)
model.train(num_iterations=1000, learning_rate=10)

"""# **MEASURE SIMILARITY**"""

DOT = 'dot'
COSINE = 'cosine'

def compute_scores(query_embedding, item_embeddings, metric=DOT):
  u = query_embedding
  V = item_embeddings

  if metric == COSINE:
    V = V / np.linalg.norm(V, axis=1, keepdims=True)
    u = u / np.linalg.norm(u)

  scores = V.dot(u.T)

  return scores

"""# **INFERENCE**"""

def user_recommendations(model, measure=DOT, exclude_rated=True, k=6):
  if USER_RATINGS:
    scores = compute_scores(
        model.embeddings['user_id'][942],
        model.embeddings['movie_id'],
        measure
    )
    score_key = measure + ' score'

    df = pd.DataFrame({
       score_key : list(scores),
        'movie_id' : movies['movie_id'],
        'title' : movies['title'],
        'genre' : movies['all_genres'],
    })

  if exclude_rated:
    rated_movies = ratings[ratings.user_id == "942"]["movie_id"].values
    df = df[df.movie_id.apply(lambda movie_id: movie_id not in rated_movies)]



  display.display(df.sort_values(score_key, ascending=False).head(k))

USER_RATINGS=True
user_recommendations(model, measure=DOT, k=6)
user_recommendations(model, measure=COSINE, k=6)

def movie_neighbors(model, title_substring, measure=DOT, k=6):
  # Mencari film berdasarkan judul yang dimasukkan.
  ids =  movies[movies['title'].str.contains(title_substring)].index.values
  titles = movies.iloc[ids]['title'].values
  if len(titles) == 0:
    raise ValueError("Found no movies with title %s" % title_substring)
  print("Nearest neighbors of : %s." % titles[0])
  if len(titles) > 1:
    print("[Found more than one matching movie. Other candidates: {}]".format(
        ", ".join(titles[1:])))
  movie_id = ids[0]
  scores = compute_scores(
      model.embeddings["movie_id"][movie_id], model.embeddings["movie_id"],
      measure)
  score_key = measure + ' score'
  df = pd.DataFrame({
      score_key: list(scores),
      'titles': movies['title'],
      'genres': movies['all_genres']
  })
  display.display(df.sort_values([score_key], ascending=False).head(k))

movie_neighbors(model, "fast", DOT)
movie_neighbors(model, "fast", COSINE)

