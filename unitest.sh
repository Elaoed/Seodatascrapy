#!/bin/bash


url_list=("newdun.com" "aaa.com" "cnblogs.com" "ipc.me" "sina.com" "163.com" "pubu.io" "yiqixie.com")
# url_list=("newdun.com")

echo "Starting..................."


function test_link(){

	echo "Testing getDeadLink..........."
	for url in ${url_list[@]}
		do
		curl -X POST -d "domain=${url}" localhost:5003/getDeadLink
		echo  
		echo "================================================="
	done
}

function test_web(){
	echo "Testing getWebInfo..........."
	for url in ${url_list[@]}
	do
		curl -X POST -d "domain=${url}" localhost:5003/getWebInfo
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
		curl -X POST -d "domain=${url}&search_engine=${engine}&keyword=${keyword}" localhost:5003/getKeywordRank
		echo
		echo "==================================================="
	done		
}

# test_web
# test_link
test_key_word



echo "Finished .................."
echo "==========================="
