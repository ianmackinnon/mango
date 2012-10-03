<?php
// YOU MUST FILL THESE VALUES IN AND KEEP THEM UPDATED!
$pagetitle = "Map of the arms trade";
$pagecreated = "2 August 2012";
$author = "CAAT";
$pagedescription = "Expose and challenge the arms trade on your doorstep with CAAT's map of the arms trade.";
$keywords = "mapping";
$pageupdated = "";

$PAGE_FULL_WIDTH = true;

include("{$_SERVER['DOCUMENT_ROOT']}/includes/library.php");
?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<?php include("{$_SERVER['DOCUMENT_ROOT']}/includes/metadata.php"); ?>
	</head>
	<body class="fullwidth">
		<div id="pagewrapper">
			<?php include("{$_SERVER['DOCUMENT_ROOT']}/includes/page-header.php"); ?>
			<div id="mapping"></div>
			<?php include("{$_SERVER['DOCUMENT_ROOT']}/includes/page-footer.php"); ?>
		</div>
	</body>
</html>
