#!/bin/bash

url_list=("newdun.com" "aaa.com" "bykikio.com" "027hpit.com" "lem8.com" '027kegongchang.com' 'hnfvc.com' "cnblogs.com" "ipc.me" "sina.com" "163.com" "pubu.io" "yiqixie.com" "1ting.com" "wo99.net" "kktv1.com")

INTERFACE=("getAlexa" "getWeight" "getDeadLink" "getServerInfo" "getWebInfo" "getInclude")
INTERFACE=("getInclude")
master_token='NuFOOb2OokoO2YrI6DkNHqWjBXUhvZdV'


function test_random(){
	call=${INTERFACE[$[RANDOM % ${#INTERFACE[@]}]]}
	url=${url_list[$[RANDOM % ${#url_list[@]}]]}
	echo "Testing ${url}------${call}..........."
	curl -X POST -d "domain=${url}&master_token=${master_token}" localhost:3035/${call}
	echo
	echo "================================================="
}
function test_order(){
	for url in ${url_list[@]}
	do
		call=${INTERFACE[$[RANDOM % ${#INTERFACE[@]}]]}
		echo "Testing ${url}------${call}..........."
		curl -X POST -d "domain=${url}&master_token=${master_token}" localhost:3035/${call}
		echo
		echo "================================================="
	done
}
# function test_link(){

# 	echo "Testing getDeadLink..........."
# 	for url in ${url_list[@]}
# 		do
# 		curl -X POST -# -d "domain=${url}&master_token=${master_token}" localhost:3035/getDeadLink
# 		echo  
# 		echo "================================================="
# 	done
# }

# function test_web(){
# 	echo "Testing getWebInfo..........."
# 	for url in ${url_list[@]}
# 	do
# 		curl -X POST -# -d "domain=${url}&master_token=${master_token}" localhost:3035/getWebInfo
# 		echo
# 		echo "================================================="
# 	done

# }



RANENGINE=('baidu' 'sogou' '360')
KEYWORDS=('牛盾' '博客园' 'office' '网易')
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
echo "Starting..................."

# curl -X POST -d "domain=abc.com&master_token=${master_token}&search_engine=sogou&keyword=关键字" 192.168.199.21:3035/getKeywordRank
for i in `seq 10`
do
	test_random
done
# test_order
# curl -X POST -d "domain=newdun.com&master_token=${master_token}" localhost:5003/getWebInfo
# echo
# test_web	
# test_link
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


echo
echo "Finished .................."
echo "==========================="
