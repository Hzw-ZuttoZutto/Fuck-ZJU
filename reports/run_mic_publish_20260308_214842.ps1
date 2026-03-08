chcp 65001 > $null
$env:PYTHONIOENCODING='utf-8'
$py='D:\All_The_App\anaconda3\envs\fuckclass\python.exe'
$ff='D:\All_The_App\Anaconda3\envs\fuckclass\Library\bin\ffmpeg.exe'
& $py -m src.main mic-publish --target-url http://127.0.0.1:18765 --mic-upload-token e2e_69f1fd8b35 --device "麦克风阵列 (适用于数字麦克风的英特尔® 智音技术)" --rt-pipeline-mode stream --stream-frame-duration-ms 120 --request-timeout-sec 20 --retry-base-sec 1.0 --retry-max-sec 12.0 --ffmpeg-bin $ff
