# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "be2bb30e-55f7-4334-abd5-d7e59b417dc4",
# META       "default_lakehouse_name": "Processed",
# META       "default_lakehouse_workspace_id": "c68641a8-4de4-4f57-aa3b-58574fb9c68d",
# META       "known_lakehouses": [
# META         {
# META           "id": "be2bb30e-55f7-4334-abd5-d7e59b417dc4"
# META         },
# META         {
# META           "id": "1a136eaf-6b18-4e19-ae01-9c6612fd4f1c"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Libraries

# CELL ********************

from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF, StringIndexer, VectorAssembler, IndexToString
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
import mlflow 
from pyspark.sql.functions import sha2, concat_ws
# Import the AutoML class from the FLAML package
from flaml import AutoML
from flaml.automl.spark.utils import to_pandas_on_spark
from synapse.ml.predict import MLFlowTransformer

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # Main

# CELL ********************

training_df = spark.sql("SELECT Description,CAST(Amount AS Double) AS Amount,Category FROM Processed.TraningData") 

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Convert string labels to numeric values using StringIndexer
indexer = StringIndexer(inputCol="Category", outputCol="CategoryIndex")

# Fit the StringIndexer separately to access labels
indexer_model = indexer.fit(training_df)

# Tokenization of the 'Description' column
tokenizer = Tokenizer(inputCol="Description", outputCol="words")

# Stop words removal
stopwords_remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

# TF-IDF Vectorization
hashingTF = HashingTF(inputCol="filtered_words", outputCol="rawFeatures", numFeatures=10000)
idf = IDF(inputCol="rawFeatures", outputCol="textFeatures")

# VectorAssembler to combine text features and numerical 'Amount' column
assembler = VectorAssembler(inputCols=["textFeatures", "Amount"], outputCol="features")

# Logistic Regression model
lr = LogisticRegression(featuresCol="features", labelCol="CategoryIndex")

# Convert prediction back to original category labels using the fitted indexer model's labels
label_converter = IndexToString(inputCol="prediction", outputCol="predictedCategory", labels=indexer_model.labels)

# Pipeline
pipeline = Pipeline(stages=[indexer_model, tokenizer, stopwords_remover, hashingTF, idf, assembler, lr, label_converter])

model = pipeline.fit(training_df)


# Split data into training and test sets
#(trainingData, testData) = training_df.randomSplit([0.8, 0.2])

# Train the model
#model = pipeline.fit(trainingData)

# Make predictions
# predictions = model.transform(testData)

# Show predictions with original category labels
# predictions.show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


df = spark.sql("SELECT AccountName,Date,Description,CAST(Amount AS Double) AS Amount From Processed.ProcessedCSV")    
new_df = model.transform(df)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

formatted_df= new_df.select('AccountName','Date','Description','Amount','predictedCategory').withColumnRenamed('predictedCategory','Category')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

formatted_df.createOrReplaceTempView('CategorisedTransaction')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

final_df = formatted_df.withColumn("transactionId", sha2(concat_ws("||", *formatted_df.columns), 256))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

final_df.write.format('delta').mode("overwrite").saveAsTable('Transaction')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
