<?php
    $header='http://127.0.0.1/nyanstock/Apps/MarketLogs/api/v1/';
    $urls=array(
        'admin_dbedit.php?c=spec&m=BitflyerLightning_FX_BTC_JPY',
        'dailyohlcv.php?m=BitflyerLightning_FX_BTC_JPY&t=20190202',
    );


?>
<html>
    <body>
        <?php
            for($i=0;$i<count($urls);$i++){
                print('<a href="'.$header.$urls[$i].'">'.$urls[$i].'</a>');
            }
        ?>
    </body>
</html>