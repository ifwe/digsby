TARGET_ROOT = jangle
TARGET = $(TARGET_ROOT).pyd

.PHONY: sip clean mostlyclean distclean

all: Makefile sipAPI$(TARGET_ROOT).h

Makefile sipAPI$(TARGET_ROOT).h sip: configure.py make_all_sip.py
	@../../../../dpython/python.exe configure.py

install: $(TARGET)
	@cmd //C if not exist "../../../build/platlib_win32_26" mkdir "../../../build/platlib_win32_26"
	-cp -f libexpat.dll ../../../build/platlib_win32_26/
	-cp -f $(TARGET) "../../../build/platlib_win32_26/$(TARGET)"

clean:
	-rm *.pyc
	-rm sip*.obj
	-rm *.pdb
	-rm $(TARGET)
	-rm $(TARGET).manifest
	-rm $(TARGET_ROOT).lib
	-rm $(TARGET_ROOT).exp
	-rm $(TARGET_ROOT).sbf
	-rm all.sip

distclean: clean
	-rm sip*.cpp
	-rm sip*.h
	-rm Makefile
	-rm -rf cache

clobber: distclean mostlyclean clean

%: force
	-@$(MAKE) -f Makefile $@
force: ;
