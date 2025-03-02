CREATE PROCEDURE DeleteDuplicateTransaction
    @TransactionId VARCHAR(255)
AS
BEGIN
    -- Use a transaction to ensure atomicity
    DROP TABLE IF EXISTS [TempTableName]
    BEGIN TRANSACTION;
    -- Generate a unique table name using the session I
    
        WITH ranked_transactions AS (
        SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY transactionId ORDER BY LastUpdatedDateTime desc) as rn
                FROM [Transaction]
                WHERE transactionId = @TransactionId
            )
            SELECT 
            transactionId,Date,Description,Amount,Category,Month,Year,Quarter,Week,LastUpdatedDateTime,AccountName
            INTO [TempTableName]
             FROM ranked_transactions
            WHERE rn = 1

        DELETE  FROM [Transaction]
                WHERE transactionId = @TransactionId

    INSERT INTO [Transaction]
    SELECT * FROM [TempTableName]
    -- Drop the unique temp table
   DROP TABLE IF EXISTS [TempTableName]

    -- Commit the transaction
    COMMIT TRANSACTION;
END;