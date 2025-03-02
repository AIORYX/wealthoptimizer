CREATE TABLE [dbo].[UploadedFile] (

	[FileId] varchar(8000) NULL, 
	[AccountName] varchar(8000) NULL, 
	[FileName] varchar(8000) NULL, 
	[Description] varchar(8000) NULL, 
	[LastUpdatedDateTime] datetime2(2) NULL, 
	[ProcessingStatus] varchar(50) NULL, 
	[OriginalFileName] varchar(8000) NULL
);

