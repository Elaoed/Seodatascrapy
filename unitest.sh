#!/bin/bash


# url_list=("newdun.com" "aaa.com" "cnblogs.com" "ipc.me" "sina.com" "163.com" "pubu.io" "yiqixie.com")
url_list=("newdun.com" "aaa.com" "bykikio.com" "027hpit.com" "lem8.com" '027kegongchang.com' 'hnfvc.com')

echo "Starting..................."

master_token='NuFOOb2OokoO2YrI6DkNHqWjBXUhvZdV'

function test_link(){

	echo "Testing getDeadLink..........."
	for url in ${url_list[@]}
		do
		curl -X POST -# -d "domain=${url}&master_token=${master_token}" localhost:3035/getDeadLink
		echo  
		echo "================================================="
	done
}

function test_web(){
	echo "Testing getWebInfo..........."
	for url in ${url_list[@]}
	do
		curl -X POST -# -d "domain=${url}&master_token=${master_token}" localhost:3035/getWebInfo
		echo
		echo "================================================="
	done

}
RANENGINE=('baidu' 'sogou' '360')
KEYWORDS=('牛盾' '博客园' '互联网' '机票' '热点' 'office' '网易' '新闻')
function test_key_word(){
	echo "Testing getKeywordRank..........."
	for url in ${url_list[@]}
	do
		engine=${RANENGINE[$[$RANDOM % ${#RANENGINE[@]}]]}
		keyword=${KEYWORDS[$[$RANDOM % ${#KEYWORDS[@]}]]}
		curl -X POST -d "domain=${url}&search_engine=${engine}&keyword=${keyword}&master_token=${master_token}" localhost:3035/getKeywordRank
		echo
		echo "==================================================="
	done		
}

# curl -X POST -d "domain=aaa.com&master_token=${master_token}&search_engine=baidu&keyword=123145" localhost:3035/getDeadLink
curl -X POST -d "domain=lem8.com&master_token=${master_token}" localhost:3035/getDeadLink
# echo
test_web	
test_link
# test_key_word
# url='newdun.com'
# ==================================================
# 		raise error process/flow
# ==================================================
# curl -d "domain=${url}" localhost:3035/getDeadLink
# echo
# echo "==========================================================="


# curl -d "master_token=${master_token}" localhost:3035/getDeadLink
# echo
# echo "==========================================================="
# curl -d "master_token=${master_token}&domain=${url}" localhost:3035/getDeadLink
# echo 
# echo "==========================================================="
# curl -d "master_token=${master_token}&domain=aaa" localhost:3035/getDeadLink

# curl -d "domain=${url}" localhost:3035/getWebInfo
# echo
# echo "==========================================================="
# curl -d "master_token=${master_token}&domain=${url}" localhost:3035/getWebInfo
# echo 
# echo "==========================================================="
# curl -d "master_token=${master_token}&domain=aaa" localhost:3035/getWebInfo



echo "Finished .................."
echo "==========================="
