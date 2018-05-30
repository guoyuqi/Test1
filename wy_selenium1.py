# encoding=utf8

from time import sleep
import cv2
import numpy as np
import requests
import os
import sys
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class YaoLiuSan(object):
	def __init__(self, username=None, password=None, proxies={}):
		self.login_url = 'http://reg.163.com/'
		self.username = username
		self.password = password
		self.proxies = proxies
		self.driver = webdriver.Chrome()
		# self.driver.maximize_window()

		cur_path = os.path.abspath(sys.path[0])
		cur_path = 'C:\Users\Administrator\Desktop'
		self.img_path = os.path.join(cur_path, 'imgs')
		if not os.path.exists(self.img_path):
			os.mkdir(self.img_path)

	def download(self, url):
		headers = {
			'Host': 'necaptcha.nosdn.127.net',
			'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.04'
		}
		try:
			resp = requests.get(url, headers=headers, verify=False)
		except Exception as e:
			print 'download %s failed: %s' % (url, e)
			return ''
		f_name = url.replace('https://necaptcha.nosdn.127.net/', '')
		file_name = os.path.join(self.img_path, f_name)
		with open(file_name, 'wb') as f:
			f.write(resp.content)
		return file_name

	def get_pics(self):
		tar_element = self.driver.find_element_by_class_name('yidun_bg-img')
		temp_element = self.driver.find_element_by_class_name('yidun_jigsaw')
		tar_url = tar_element.get_attribute('src')
		temp_url = temp_element.get_attribute('src')
		print '----- tar_url: ', tar_url
		print '----- temp_url: ', temp_url
		if tar_url and temp_url:
			target = self.download(tar_url)
			template = self.download(temp_url)
		else:
			print 'get pics error'
			target = template = ''

		return target, template

	def get_distance(self, target, template):
		img_rgb = cv2.imread(target)
		img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)	# 将图像从一个颜色空间转换为另一个颜色空间
		temp = cv2.imread(template, 0)
		run = 1
		w, h = temp.shape[::-1]
		res = cv2.matchTemplate(img_gray, temp, cv2.TM_CCOEFF_NORMED)
		L = 0
		R = 1
		flag = 0
		# while run < 20:
		while not flag:
			run += 1
			threshold = (R + L) / 2.
			# print threshold
			if threshold < 0:
				print 'get_distance Error'
				return None
			loc = np.where(res >= threshold)
			# print len(loc[1])
			if len(loc[1]) > 1:
				L += (R - L) / 2.
			elif len(loc[1]) == 1:
				print '目标区域起点x坐标为：%d' % loc[1][0]
				flag = 1
				# break
			else:
				R -= (R - L) / 2.
		# 展示圈出来的区域
		# for pt in zip(*loc[::-1]):
		# 	cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (7, 249, 151), 2)
		# cv2.imshow('Detected', img_rgb)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()

		try:
			os.remove(target)
		except Exception as e:
			print 'remove target error: %s' % e
		try:
			os.remove(template)
		except Exception as e:
			print 'remove template error: %s' % e

		return loc[1][0]

	def get_track(self, distance):
		track = []
		current = 0
		mid = distance * 3 / 5.
		t = 0.2
		v = 0
		while current < distance:
			if current < mid:
				a = 2.
			else:
				a = -3.
			v0 = v
			v = v0 + a * t
			move = v0 * t + 1 / 2. * a * t * t
			current += move
			track.append(round(move))
		return track

	def move_slider(self, slider, distance):
		distance += 13
		action = ActionChains(self.driver)
		action.click_and_hold(slider).perform()
		action.reset_actions()	# 清除之前的action
		track = self.get_track(distance)
		for i in track:
			action.move_by_offset(xoffset=i, yoffset=0).perform()
			action.reset_actions()
		sleep(0.5)
		action.release().perform()
		sleep(1)

	def login(self):
		try:
			self.driver.get(self.login_url)
		except Exception as e:
			print 'open url failed'
			self.driver.quit()
			return {'ret_code': 0, 'description': '打开登录页失败'}
		
		# 切换iframe
		try:
			iframe = self.driver.find_element_by_xpath("//iframe[contains(@id, 'iframe')]")
		except Exception as e:
			print 'get iframe failed: ', e
			self.driver.quit()
			return {'ret_code': 0, 'description': '未找到iframe'}
		self.driver.switch_to.frame(iframe)

		# 等待验证码加载完成
		try:
			check = WebDriverWait(self.driver, 10).until(
				EC.text_to_be_present_in_element((By.CLASS_NAME, 'yidun_tips__text'), u'向右滑动滑块填充拼图')
			)
			# slider = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'yidun_slider')))
			# pics = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'yidun_bg-img')))
		except Exception as e:
			print 'check load failed: %s' % e
			self.driver.quit()
			return {'ret_code': 0, 'description': '获取滑块失败'}
		sleep(5)

		# 获取图片
		target, template = self.get_pics()
		if not target or not template:
			self.driver.quit()
			return {'ret_code': 0, 'description': '获取图片失败'}

		# 获取移动距离
		distance = self.get_distance(target, template)
		distance = distance * 330 / 480.    # 页面上操作的图片和实际下载的图片大小不一样，所以要按比例计算滑动距离

		# sleep(1000)

		# 移动滑块
		# distance = 44
		slider = self.driver.find_element_by_class_name('yidun_slider')
		self.move_slider(slider, distance)

		try:
			check = WebDriverWait(self.driver, 5).until(
				EC.text_to_be_present_in_element((By.CLASS_NAME, 'yidun_tips__text'), u'向右滑动滑块填充拼图')
				)
			# print '滑块验证未通过'
			self.driver.quit()
			return {'ret_code': 0, 'description': '滑块验证未通过'}
		except Exception as e:
			# print e
			print '滑块验证通过'

		# 输入账号密码
		self.driver.find_element_by_name('email').clear()
		self.driver.find_element_by_name('email').send_keys(self.username)
		self.driver.find_element_by_name('password').clear()
		self.driver.find_element_by_name('password').send_keys(self.password)

		# 点击登录
		try:
			self.driver.find_element_by_id('dologin').click()
		except Exception as e:
			print 'click login failed: %s' % e
			self.driver.quit()
			return {'ret_code': 0, 'description': '登录失败'}
		sleep(3)

		# 继续登录
		try:
			self.driver.find_element_by_xpath('//div[@class="btnbox"]/a[1]').click()
		except Exception as e:
			print 'continue login failed: %s' % e

		sleep(2)

		try:
			btnbox = self.driver.find_element_by_class_name('btnbox')
			self.driver.quit()
			return {'ret_code': 0, 'description': '登录跳转失败'}
		except:
			pass
		cook_all = self.driver.get_cookies()
		# print '---- cook_all: ', cook_all
		cookies = {}
		for item in cook_all:
			name = item.get('name').encode('utf8')
			value = item.get('value').encode('utf8')
			cookies[name] = value
		print '---- cookies: ', cookies

		sleep(6)
		self.driver.quit()
		return {'ret_code': 0, 'description': '登录成功'}

if __name__ == '__main__':
	username = '123'
	password = '456'
	obj = YaoLiuSan(username, password)
	result = obj.login()
	for k, v in result.items():
		print k, v