

def time_formatting( t):
	t = t.split(":")
	t = [int(i) for i in t]
	def minute(m):
		if m == 1:
			return _("دقيقة واحدة")
		elif m == 2:
			return _("دقيقتان")
		elif m >=3 and m <=10:
			return _("{} دقائق").format(m)
		else:
			return _("{} دقيقة").format(m)
	def second(s):
		if s == 1:
			return _("ثانية")
		elif s == 2:
			return _("ثانيتين")
		elif s >= 3 and s <= 10:
			return _("{} ثواني").format(s)
		else:
			return _("{} ثانية").format(s)
	def hour(h):
		if h == 1:
			return _("ساعة")
		elif h == 2:
			return _("ساعتان")
		elif h >= 3 and h <=10:
			return _("{} ساعات").format(h)
		else:
			return _("{} ساعة").format(h)
	if len(t) == 1:
		return second(t[0])
	elif len(t) == 2:
		return _("{} و{}").format(minute(t[0]), second(t[1]))
	elif len(t) == 3:
		return _("{} و{} و{}").format(hour(t[0]), minute(t[1]), second(t[2]))

	