/**
 * jQuery lightBox plugin
 * This jQuery plugin was inspired and based on Lightbox 2 by Lokesh Dhakar (http://www.huddletogether.com/projects/lightbox2/)
 * and adapted to me for use like a plugin from jQuery.
 * @name jquery-lightbox-0.5.js
 * @author Leandro Vieira Pinho - http://leandrovieira.com
 * @version 0.5
 * @date April 11, 2008
 * @category jQuery plugin
 * @copyright (c) 2008 Leandro Vieira Pinho (leandrovieira.com)
 * @license CC Attribution-No Derivative Works 2.5 Brazil - http://creativecommons.org/licenses/by-nd/2.5/br/deed.en_US
 * @example Visit http://leandrovieira.com/projects/jquery/lightbox/ for more informations about this jQuery plugin
 */

// Offering a Custom Alias suport - More info: http://docs.jquery.com/Plugins/Authoring#Custom_Alias

function center(left, top, width, height) {
  if (width == null && height == null) {
    width = left;
    height = top;
    top = 0;
    left = 0;
  }

  return [left + (width / 2), top + (height / 2)];
}
(function($) {
    /**
     * $ is an alias to jQuery object
     *
     */
    $.fn.lightBox = function(settings) {
        // Settings to configure the jQuery lightBox plugin how you like
        settings = jQuery.extend({
            // Configuration related to overlay
            overlayBgColor:         '#000',        // (string) Background color to overlay; inform a hexadecimal value like: #RRGGBB. Where RR, GG, and BB are the hexadecimal values for the red, green, and blue values of the color.
            overlayOpacity:            0.0,        // (integer) Opacity value to overlay; inform: 0.X. Where X are number from 0 to 9
            // Configuration related to navigation
            fixedNavigation:        false,        // (boolean) Boolean that informs if the navigation (next and prev button) will be fixed or not in the interface.
            fixedDataBox:           false,
            imageDir:               'images',
            // Configuration related to images
            imageLoading:           'lightbox-blank.gif',                // (string) Path and the name of the loading icon
            imageBtnPrev:           'lightbox-btn-prev.gif',        // (string) Path and the name of the prev button image
            imageBtnNext:           'lightbox-btn-next.gif',        // (string) Path and the name of the next button image
            imageBtnClose:          'lightbox-blank.gif',                // (string) Path and the name of the close btn
            imageBlank:             'lightbox-blank.gif',            // (string) Path and the name of a blank image (one pixel)
            imageContext:           'lightbox-blank.gif',
            // Configuration related to container image box
            containerBorderSize:    0,            // (integer) If you adjust the padding in the CSS for the container, #lightbox-container-image-box, you will need to update this value
            containerResizeSpeed:   100,        // (integer) Specify the resize duration of container image. These number are miliseconds. 100 is default.
            // Configuration related to texts in caption. For example: Image 2 of 8. You can alter either "Image" and "of" texts.
            txtImage:               'Image',    // (string) Specify text "Image"
            txtOf:                  'of',        // (string) Specify text "of"
            // Configuration related to keyboard navigation
            keyToClose:             'c',        // (string) (c = close) Letter to close the jQuery lightBox interface. Beyond this letter, the letter X and the SCAPE key is used to.
            keyToPrev:              'p',        // (string) (p = previous) Letter to show the previous image
            keyToNext:              'n',        // (string) (n = next) Letter to show the next image.
            wrapNav:                false,
            dataBoxFirst:           false,
            clickLoadingClose:      true,
            clickBoxClose:          true,
            linkContextFunction:    function () { return ''; },
            onShowFunction:         function () { return ''; },
            haveShown:              false,
            delayUntilShown:        [],
            onInitFunction:         function () { return ''; },
            lengthTextFunction:     function (arrayLen) { return arrayLen; },
            realIndexFunction:      function (arrayIdx) { return arrayIdx; },
            imgIdFunction:          function (obj) { return obj.getAttribute('href'); },
            showContext:            false,
            windowPadding:          16,
            changeCounterAfterSlide:true,
            iconOffset:             4,
            // Don´t alter these variables in any way
            imageArray:             [],
            activeImage:            0,
            parentSelector:         null,
        },settings);
        // Caching the jQuery object with all elements matched
        var jQueryMatchedObj = this; // This, in this context, refer to jQuery object
        /**
         * Initializing the plugin calling the start function
         *
         * @return boolean false
         */
        function _initialize() {
            window._activeLightBox = { destroy: _finish, };
            $('.hover-icon').hide();
            _start(this,jQueryMatchedObj); // This, in this context, refer to object (link) which the user have clicked
            settings.haveShown = false;
            settings.onInitFunction(this, jQueryMatchedObj);
            return false; // Avoid the browser following the link
        }
        /**
         * Start the jQuery lightBox plugin
         *
         * @param object objClicked The object (link) whick the user have clicked
         * @param object jQueryMatchedObj The jQuery object with all elements matched
         */
        function _start(objClicked,jQueryMatchedObj) {
            // Hide some elements to avoid conflict with overlay in IE. These elements appear above the overlay.
            $('embed, object, select').css({ 'visibility' : 'hidden' });
            // Call the function to create the markup structure; style some elements; assign events in some elements.
            // Unset total images in imageArray
            settings.imageArray.length = 0;
            // Unset image active information
            settings.activeImage = 0;
            if (jQueryMatchedObj.data('imageArray')){
                storedArray = jQueryMatchedObj.data('imageArray');
                for ( var i = 0; i < storedArray.length; i++ ) {
                    settings.imageArray.push(storedArray[i]);
                }
            // We have an image set? Or just an image? Let´s see it.
            } else if ( jQueryMatchedObj.length == 1 ) {
                settings.imageArray.push(new Array(objClicked.getAttribute('href'),
                                                   objClicked.getAttribute('title'),
                                                   objClicked.getAttribute('context'),
                                                   $(objClicked).offset(),
                                                   objClicked.getAttribute('alt'),
                                                   settings.imgIdFunction(objClicked)
                                                   ));
            } else {
                // Add an Array (as many as we have), with href and title attributes, inside the Array that stores the image references
                for ( var i = 0; i < jQueryMatchedObj.length; i++ ) {
                    settings.imageArray.push(new Array(jQueryMatchedObj[i].getAttribute('href'),
                                                       jQueryMatchedObj[i].getAttribute('title'),
                                                       jQueryMatchedObj[i].getAttribute('context'),
                                                       $(jQueryMatchedObj[i]).offset(),
                                                       jQueryMatchedObj[i].getAttribute('alt'),
                                                       settings.imgIdFunction(jQueryMatchedObj[i])
                                                       ));
                }
            }
            while ( settings.imageArray[settings.activeImage][5] != settings.imgIdFunction(objClicked) ) {
                settings.activeImage++;
            }
            // Call the function that prepares image exhibition
            //$('#lightbox-image,#lightbox-container-image-data-box,#lightbox-image-details-currentNumber').hide();
            _set_interface();
            _set_image_to_view();
        }

        function _set_interface() {
            // Apply the HTML markup into body tag
            function __get_loading_content() {
            return '<div id="lightbox-loading">' +
                 '<div id="lightbox-loading-inner">' +
                  '<a href="#" id="lightbox-loading-link">' +
                   '<img src="' + settings.imageDir + "/" + settings.imageLoading + '">' +
                  '</a>' +
                 '</div>' +
                '</div>';
            }
            function __get_image_box() {
             return '<div id="lightbox-container-image-box">' +
              '<div id="lightbox-container-image">' +
               '<img id="lightbox-image">' +
                '<div style="" id="lightbox-nav">' +
                 '<a href="#" id="lightbox-nav-btnPrev"></a>' +
                 '<a href="#" id="lightbox-nav-btnNext"></a>' +
                '</div>' +
                //__get_loading_content() +
               '</div>' +
              '</div>';
            }
            function __get_context_button_content() {
             if (!settings.showContext) {
              return '';
             }

             return '<a id="lightbox-secNav-btnContext" href="#">' +
                     '<img src="' + settings.imageDir + '/' + settings.imageContext + '"></a>';
            }

            function __get_close_button_content() {
             return '<a href="#" id="lightbox-secNav-btnClose">' +
                     '<img src="' + settings.imageDir + '/' + settings.imageBtnClose + '"></a>';
            }

            function __get_image_data_box() {
             return '<div id="lightbox-container-image-data-box" class="header">' +
               '<div id="lightbox-container-image-data">' +
               '<div id="lightbox-secNav">' +
               __get_close_button_content() +
               __get_context_button_content() +
               '</div>' +
                '<div id="lightbox-image-details">' +
                '<span id="lightbox-image-details-currentNumber" ' + '>' +
                /*'style="padding-' + (settings.dataBoxFirst ? 'top' : 'bottom') + ':1em;">' +*/
                '</span>' +
                '<span id="lightbox-image-details-caption"></span>' +
               '</div>' +

               '</div>' +
              '</div>';
            }
            var top = __get_loading_content() +
                      '<div id="jquery-overlay"></div>' +
                       '<div id="jquery-lightbox">';

            var mid = "";

            if (settings.dataBoxFirst) {
             mid = __get_image_data_box() + __get_image_box();
            } else {
             mid = __get_image_box() + __get_image_data_box();
            }
            var bottom = '</div>'

            _add_to_parent(top + mid + bottom);

            if (settings.dataBoxFirst) {
             $("#lightbox-container-image-data-box").css({borderBottomStyle: "none"});
            } else {
             $("#lightbox-container-image-data-box").css({borderTopStyle: "none"});
            }
            // Get page sizes
            var arrPageSizes = ___getPageSize();
            // Style overlay and show it

            // # ANIMATE
            $('#jquery-overlay').css({
                background:            settings.overlayBgColor,
                opacity:            settings.overlayOpacity,
                width:                arrPageSizes[0],
                height:                arrPageSizes[1]
            }).fadeIn();
            // Get page scroll
            var arrPageScroll = ___getPageScroll();
            // Calculate top and left offset for the jquery-lightbox div object and show it
            scrCenter = center(arrPageScroll[0], arrPageScroll[1], arrPageSizes[2], arrPageSizes[3]);
            $('#jquery-lightbox').show().css({
                width: 0,
                height: 0,
                left: scrCenter[0],
                top: scrCenter[1],
            },
            { queue: false,
              duration: settings.containerResizeSpeed
            });
            // Assigning click events in elements to close overlay
            if (settings.clickBoxClose) {
             $('#jquery-lightbox').click(function () { _finish(); return false; } );
            }

            $('#jquery-overlay').click(function() {
                _finish();
                return false;
            });

            if (settings.showContext) {
             $('#lightbox-secNav-btnContext').attr("href", settings.imageArray[settings.activeImage][2]);
            }
            if (settings.clickLoadingClose) {
             $('#lightbox-loading-link').click(function() { _finish(); return false; });
            }

            // make clicking these do nothing
            $('#lightbox-nav-btnPrev').click(function () {return false;});
            $('#lightbox-nav-btnNext').click(function () {return false;});
            // Assign the _finish function to lightbox-loading-link and lightbox-secNav-btnClose objects
            $('#lightbox-secNav-btnClose').click(function() { _finish(); return false; });
            // If window was resized, calculate the new overlay dimensions
            $(window).resize(function() {
                // Get page sizes
                var arrPageSizes = ___getPageSize();
                // Style overlay and show it
                $('#jquery-overlay').css({
                    width:        arrPageSizes[0],
                    height:        arrPageSizes[1]
                });
                // Get page scroll
                var arrPageScroll = ___getPageScroll();
                // Calculate top and left offset for the jquery-lightbox div object and show it
                scrCenter = center(arrPageScroll[0], arrPageScroll[1], arrPageSizes[2], arrPageSizes[3]);
                $('#jquery-lightbox').css({
                    left: scrCenter[0],
                    top: scrCenter[1],
                });
            });
        }
        /**
         * Prepares image exibition; doing a image´s preloader to calculate it´s size
         *
         */
        function _set_image_to_view(do_on_show) { // show the loading
            // Bring back border along the edge shared with the data box
            if (!settings.fixedDataBox) {
                if (settings.dataBoxFirst) {
                 $("#lightbox-container-image-box").css({borderTopStyle: "solid"});
                } else {
                 $("#lightbox-container-image-box").css({borderBottomStyle: "solid"});
                }
            }
            if (settings.wrapNav) {
             if (settings.activeImage < 0) {
              // go to last image
              settings.activeImage = settings.imageArray.length - 1;
             } else if (settings.activeImage >= settings.imageArray.length) {
             // go to first image
              settings.activeImage = 0;
             }
            }
            if ( !settings.fixedDataBox) {
                //$('#lightbox-image,#lightbox-container-image-data-box,#lightbox-image-details-currentNumber').hide();
            }
            if ( !settings.fixedNavigation ) {
                // Hide some elements
                //$('#lightbox-nav,#lightbox-nav-btnPrev,#lightbox-nav-btnNext').hide();
            }
            if (settings.showContext) {
             $('#lightbox-secNav-btnContext').attr("href", settings.imageArray[settings.activeImage][2]);
            }

            // Image preload process
            var objImagePreloader = new Image();
            objImagePreloader.onload = function() {
                $('#lightbox-loading').hide();
                $('#lightbox-image').attr('src',settings.imageArray[settings.activeImage][0]);
                resized = _get_proper_image_size(objImagePreloader.width, objImagePreloader.height);

                //$('#lightbox-image').css({width: resized[0], height: resized[1]});
                // Perfomance an effect in the image container resizing it
                _resize_container_image_box(resized[0], resized[1], $("#lightbox-container-image-box").is(":hidden"), do_on_show);
                //    clear onLoad, IE behaves irratically with animated gifs otherwise
                objImagePreloader.onload=function(){};
                objImagePreloader.loaded = true;
            };
            objImagePreloader.src = settings.imageArray[settings.activeImage][0];
            objImagePreloader.loaded = false;

            var arrPageScroll = ___getPageScroll();
            var arrPageSizes = ___getPageSize();
            resized = _get_proper_image_size(objImagePreloader.width, objImagePreloader.height);
            scrCenter = center(arrPageScroll[0], arrPageScroll[1], arrPageSizes[2], arrPageSizes[3]);
            $('#lightbox-loading').css({
                top:  scrCenter[1] - ($('#lightbox-loading').height() / 2),
                left: scrCenter[0] - ($('#lightbox-loading').width()  / 2),
            });

            // Show the loading
            if (!objImagePreloader.loaded) {
                $('#lightbox-loading').show();
            }

            if ( !settings.changeCounterAfterSlide ){
                // If we have a image set, display 'Image X of X'
                if ( settings.imageArray.length > 1 ) {
                    $('#lightbox-image-details-currentNumber').html((settings.txtImage || settings.imageArray[settings.activeImage][4] || "")+ ' ' + ( settings.realIndexFunction(settings.activeImage) + 1 ) + ' ' + settings.txtOf + ' ' + settings.lengthTextFunction(settings.imageArray.length)).show();
                }
            }
        };

        /**
        */
        function _get_proper_image_size(iw, ih) {
            var pagesize = ___getPageSize();
            var x = pagesize[2] - (settings.containerBorderSize*2) - (settings.windowPadding*2);
            var y = pagesize[3] - (settings.containerBorderSize*2) - (settings.windowPadding*2) - 60;
            var imageWidth = iw;
            var imageHeight = ih;
            if (imageWidth > x) {
                    imageHeight = imageHeight * (x / imageWidth);
                    imageWidth = x;
                    if (imageHeight > y) {
                            imageWidth = imageWidth * (y / imageHeight);
                            imageHeight = y;
                    }
            } else if (imageHeight > y) {
                    imageWidth = imageWidth * (y / imageHeight);
                    imageHeight = y;
                    if (imageWidth > x) {
                            imageHeight = imageHeight * (x / imageWidth);
                            imageWidth = x;
                    }
            }
            return [imageWidth, imageHeight];
        }
        /**
         * Perfomance an effect in the image container resizing it
         *
         * @param integer intImageWidth The image´s width that will be showed
         * @param integer intImageHeight The image´s height that will be showed
         */
        function _resize_container_image_box(intImageWidth,intImageHeight, is_hidden, do_on_show) {
            // Get current width and height
            var intCurrentWidth = $('#lightbox-container-image-box').width();
            var intCurrentHeight = $('#lightbox-container-image-box').height();
            // Get the width and height of the selected image plus the padding
            var intWidth = (intImageWidth + (settings.containerBorderSize * 2)); // Plus the image´s width and the left and right padding value
            var intHeight = (intImageHeight + (settings.containerBorderSize * 2)); // Plus the image´s height and the left and right padding value
            // Diferences
            var intDiffW = intCurrentWidth - intWidth;
            var intDiffH = intCurrentHeight - intHeight;
            // Perfomance the effect

            $('#lightbox-container-image-data-box').css({ width: intImageWidth });
            $('#lightbox-nav-btnPrev,#lightbox-nav-btnNext').css({ height: intImageHeight + (settings.containerBorderSize * 2) });
            // # ANIMATE

            lbcidb_height = $('#lightbox-container-image-data-box').height();
            lbcidb_width = intImageWidth;
            if (is_hidden) {
                $('#lightbox-container-image-data-box').css({height: 0, width: 0});
                $('#lightbox-image').css({height: 0, width: 0});
                $('#lightbox-container-image-box').css({height: 0, width: 0});
                $('#jquery-lightbox').css({height: 0, width: 0});
                setsize = "animate";
            } else {
                setsize = "css";
            }

            $('#jquery-lightbox')[setsize]({
                    top: ___getPageScroll()[1] + (___getPageSize()[3] - intImageHeight) / 2,
                    left: ___getPageScroll()[0] + (___getPageSize()[2] - intImageWidth) / 2,
                    width: intImageWidth,
                    height: intImageHeight + lbcidb_height,
            }, { queue: false,
                 duration: settings.containerResizeSpeed,
                 complete: function () {_show_image(do_on_show);}
            });

            $('#lightbox-container-image-data-box')[setsize]({
                    height: lbcidb_height,
                    width: lbcidb_width,
                }, { queue: false, duration: settings.containerResizeSpeed }
            );

            $('#lightbox-image')[setsize]({
                    width: intWidth,
                    height: intHeight
            }, { queue: false, duration: settings.containerResizeSpeed });

            $('#lightbox-container-image-box')[setsize]({
                    width: intWidth,
                    height: intHeight,
            }, { queue: false, duration: settings.containerResizeSpeed });

            if (setsize == 'css') {
                _show_image(do_on_show);
            }

        };

        /**
         * Show the prepared image
         *
         */
        function _show_image(do_on_show) {
            $('#lightbox-loading').hide();
            // Remove border along the edge shared with the data box
            if (settings.dataBoxFirst) {
             $("#lightbox-container-image-box").css({borderTopStyle: "none"});
            } else {
             $("#lightbox-container-image-box").css({borderBottomStyle: "none"});
            }
            $('#lightbox-image-details').fadeIn("def", function(){
                if (settings.haveShown) {
                    return
                }
                settings.haveShown = true;
                for (var i = 0; i < settings.delayUntilShown.length; i++){
                    settings.delayUntilShown[i]();
                }
                settings.delayUntilShown.length = 0;
            });
            _show_image_data();
            _set_navigation();
            _preload_neighbor_images();
            if (do_on_show != false) {
                settings.onShowFunction(this);
            }
        };
        /**
         * Show the image information
         *
         */
        function _show_image_data() {

            if (!settings.fixedDataBox) {
                    //$('#lightbox-image-details-caption').hide();
            }
            if ( settings.imageArray[settings.activeImage][1] ) {
                var dash = settings.imageArray.length > 1 ? '- ' : '';
                $('#lightbox-image-details-caption').html(dash + settings.imageArray[settings.activeImage][1]).show();
            } else {
                $('#lightbox-image-details-caption').hide();
            }
            if ( settings.changeCounterAfterSlide ){
                // If we have a image set, display 'Image X of X'
                if ( settings.imageArray.length > 1 ) {
                    $('#lightbox-image-details-currentNumber').html(settings.txtImage + ' ' + ( settings.activeImage + 1 ) + ' ' + settings.txtOf + ' ' + settings.imageArray.length).show();
                }
            }
        }
        /**
         * Display the button navigations
         *
         */
        function _set_navigation() {
            $('#lightbox-nav').show();

            // Instead to define this configuration in CSS file, we define here. And it´s need to IE. Just.
            $('#lightbox-nav-btnPrev,#lightbox-nav-btnNext').css({ 'background' : 'transparent url("' + settings.imageDir + "/" + settings.imageBlank + '") no-repeat' });

            // Show the prev button
            if ( ((settings.activeImage != 0) || settings.wrapNav) && settings.imageArray.length > 1 ) {
                if ( settings.fixedNavigation ) {
                    $('#lightbox-nav-btnPrev').css({ 'background' : 'url("' + settings.imageDir + "/" + settings.imageBtnPrev + '") left 15% no-repeat' })
                        .unbind()
                        .bind('click',function() {
                            settings.activeImage = settings.activeImage - 1;
                            _set_image_to_view();
                            return false;
                        });
                } else {
                    // Show the images button for Next buttons
                    $('#lightbox-nav-btnPrev').unbind().hover(function() {
                        $(this).css({ 'background' : 'url("' + settings.imageDir + "/" + settings.imageBtnPrev + '") left 15% no-repeat' });
                    },function() {
                        $(this).css({ 'background' : 'transparent url("' + settings.imageDir + "/" + settings.imageBlank + '") no-repeat' });
                    }).show().bind('click',function() {
                        settings.activeImage = settings.activeImage - 1;
                        _set_image_to_view();
                        return false;
                    });
                }
            }

            // Show the next button, if not the last image in set
            if ( ((settings.activeImage != ( settings.imageArray.length -1 ) ) || settings.wrapNav) && settings.imageArray.length > 1 ) {
                if ( settings.fixedNavigation ) {
                    $('#lightbox-nav-btnNext').css({ 'background' : 'url("' + settings.imageDir + "/" + settings.imageBtnNext + '") right 15% no-repeat' })
                        .unbind()
                        .bind('click',function() {
                            settings.activeImage = settings.activeImage + 1;
                            _set_image_to_view();
                            return false;
                        });
                } else {
                    // Show the images button for Next buttons
                    $('#lightbox-nav-btnNext').unbind().hover(function() {
                        $(this).css({ 'background' : 'url("' + settings.imageDir + "/" + settings.imageBtnNext + '") right 15% no-repeat' });
                    },function() {
                        $(this).css({ 'background' : 'transparent url("' + settings.imageDir + "/" + settings.imageBlank + '") no-repeat' });
                    }).show().bind('click',function() {
                        settings.activeImage = settings.activeImage + 1;
                        _set_image_to_view();
                        return false;
                    });
                }
            }
            // Enable keyboard navigation
            _enable_keyboard_navigation();
        }
        /**
         * Enable a support to keyboard navigation
         *
         */
        function _enable_keyboard_navigation() {
            $(document).keydown(_keyboard_action);
        }
        /**
         * Disable the support to keyboard navigation
         *
         */
        function _disable_keyboard_navigation() {
            $(document).unbind('keydown', _keyboard_action);
        }
        /**
         * Perform the keyboard actions
         *
         */
        function _keyboard_action(objEvent) {
            // To ie
            if ( objEvent == null ) {
                keycode = event.keyCode;
                escapeKey = 27;
            // To Mozilla
            } else {
                keycode = objEvent.keyCode;
                escapeKey = objEvent.DOM_VK_ESCAPE;
            }
            // Get the key in lower case form
            key = String.fromCharCode(keycode).toLowerCase();
            // Verify the keys to close the ligthBox
            if ( ( key == settings.keyToClose ) || ( key == 'x' ) || ( keycode == escapeKey ) ) {
                _finish();
            }
            // Verify the key to show the previous image
            if ( ( key == settings.keyToPrev ) || ( keycode == 37 ) ) {
                // If we´re not showing the first image, call the previous
                if ( (settings.activeImage != 0) || settings.wrapNav ) {
                    settings.activeImage = settings.activeImage - 1;
                    _set_image_to_view();
                    _disable_keyboard_navigation();
                }
            }
            // Verify the key to show the next image
            if ( ( key == settings.keyToNext ) || ( keycode == 39 ) ) {
                // If we´re not showing the last image, call the next
                if ( (settings.activeImage != ( settings.imageArray.length - 1 )) || settings.wrapNav ) {
                    settings.activeImage = settings.activeImage + 1;
                    _set_image_to_view();
                    _disable_keyboard_navigation();
                }
            }
        }
        /**
         * Preload prev and next images being showed
         *
         */
        function _preload_neighbor_images() {
                    function preload(idx) {
                     obj = new Image();
                     obj.src = settings.imageArray[idx][0];
                    }
                    if ( (settings.imageArray.length -1) > settings.activeImage ) {
                            preload(settings.activeImage + 1);
                    } else if (settings.wrapNav) {
                            // we're at the end; preload #0
                            preload(0);
                    }
                    if ( settings.activeImage > 0 ) {
                            preload(settings.activeImage - 1);
                    } else if (settings.wrapNav) {
                            // we're at the start, preload the last one
                            preload(settings.imageArray.length -1);
                    }
        }
        /**
         * Remove jQuery lightBox plugin HTML markup
         *
         */
        function _finish() {
            // stop all fading and animations
            $.each(['#lightbox-image-details', '#jquery-lightbox', '#jquery-overlay'], function (i, id) {
                $(id).stop(true, true);
            });

            window._activeLightBox = null;
            _disable_keyboard_navigation();
            $('.hover-icon').remove();
            $('#lightbox-loading').remove();
            $('#jquery-lightbox').remove();
            $('#jquery-overlay').remove();
            // Show some elements to avoid conflict with overlay in IE. These elements appear above the overlay.
            $('embed, object, select').css({ 'visibility' : 'visible' });
        }
        /**
         / THIRD FUNCTION
         * getPageSize() by quirksmode.com
         *
         * @return Array Return an array with page width, height and window width, height
         */
        function ___getPageSize() {
            var xScroll, yScroll;
            if (window.innerHeight && window.scrollMaxY) {
                xScroll = window.innerWidth + window.scrollMaxX;
                yScroll = window.innerHeight + window.scrollMaxY;
            } else if (document.body.scrollHeight > document.body.offsetHeight){ // all but Explorer Mac
                xScroll = document.body.scrollWidth;
                yScroll = document.body.scrollHeight;
            } else { // Explorer Mac...would also work in Explorer 6 Strict, Mozilla and Safari
                xScroll = document.body.offsetWidth;
                yScroll = document.body.offsetHeight;
            }
            var windowWidth, windowHeight;
            if (self.innerHeight) {    // all except Explorer
                if(document.documentElement.clientWidth){
                    windowWidth = document.documentElement.clientWidth;
                } else {
                    windowWidth = self.innerWidth;
                }
                windowHeight = self.innerHeight;
            } else if (document.documentElement && document.documentElement.clientHeight) { // Explorer 6 Strict Mode
                windowWidth = document.documentElement.clientWidth;
                windowHeight = document.documentElement.clientHeight;
            } else if (document.body) { // other Explorers
                windowWidth = document.body.clientWidth;
                windowHeight = document.body.clientHeight;
            }
            // for small pages with total height less then height of the viewport
            if(yScroll < windowHeight){
                pageHeight = windowHeight;
            } else {
                pageHeight = yScroll;
            }
            // for small pages with total width less then width of the viewport
            if(xScroll < windowWidth){
                pageWidth = xScroll;
            } else {
                pageWidth = windowWidth;
            }
            arrayPageSize = new Array(pageWidth,pageHeight,windowWidth,windowHeight);
            return arrayPageSize;
        };
        /**
         / THIRD FUNCTION
         * getPageScroll() by quirksmode.com
         *
         * @return Array Return an array with x,y page scroll values.
         */
        function ___getPageScroll() {
            var xScroll, yScroll;
            if (self.pageYOffset) {
                yScroll = self.pageYOffset;
                xScroll = self.pageXOffset;
            } else if (document.documentElement && document.documentElement.scrollTop) {     // Explorer 6 Strict
                yScroll = document.documentElement.scrollTop;
                xScroll = document.documentElement.scrollLeft;
            } else if (document.body) {// all other Explorers
                yScroll = document.body.scrollTop;
                xScroll = document.body.scrollLeft;
            }
            arrayPageScroll = new Array(xScroll,yScroll);
            return arrayPageScroll;
        };
         /**
          * Stop the code execution from a escified time in milisecond
          *
          */
         function ___pause(ms) {
            var date = new Date();
            curDate = null;
            do { var curDate = new Date(); }
            while ( curDate - date < ms);
         };
        // Return the jQuery object for chaining. The unbind method is used to avoid click conflict when the plugin is called more than once

        function _add_to_parent(element) {
            sel = settings.parentSelector || "body";
            parent = $($(sel)[0]);
            parent.append(element);
        }

        function addHoverToElement(org_image) {
            icon = $("<div></div>").addClass("hover-icon").css({"display":"none"});
            _add_to_parent(icon);

            org_image.hover(function() {
                    click_image = function () { $(icon).hide(); $(this).hide(); return org_image.click.call(org_image); };
                    var margin_top = org_image.css("marginTop").slice(0,-2);
                    var margin_bottom = org_image.css("marginBottom").slice(0,-2);
                    var margin_left = org_image.css("marginLeft").slice(0,-2);
                    var margin_right = org_image.css("marginRight").slice(0,-2);
                    if (margin_top < 0 || margin_bottom < 0 || margin_left < 0 || margin_right < 0) {
                        var parent_ele = $(org_image);
                        var parentEls = $(org_image).parents();
                         $(parentEls).each(function(){
                            if(this.tagName == "BODY") {
                                return false;
                            } else if($(this).css("overflow") == "hidden") {
                                parent_ele = $(this);
                                return false;
                            }
                        });
                        var offset = parent_ele.offset();
                        var parent_border_top = parseInt(parent_ele.css("border-top-width"));
                        var parent_border_left = parseInt(parent_ele.css("border-left-width"));
                    } else {
                        var offset = org_image.offset();
                        var parent_border_top = parseInt(org_image.css("border-top-width"));
                        var parent_border_left = parseInt(org_image.css("border-left-width"));
                    }
                    if (!parent_border_top){ parent_border_top = 0; }
                    if (!parent_border_left){ parent_border_left = 0; }

                    var displayFlag = false;
                    $("div.hover-icon").each(function(){
                        if(parseInt($(this).css("top")) == (offset.top + settings.iconOffset + parent_border_top) &&
                           parseInt($(this).css("left")) == (offset.left + settings.iconOffset + parent_border_left)){
                            displayFlag = true;
                            curIcon = $(this);
                        }
                    });
                    if(displayFlag == false){
                        $(icon).css({"top": offset.top + settings.iconOffset + parent_border_top,
                                     "left": offset.left + settings.iconOffset + parent_border_left});
                        $("body").prepend(icon);
                    }
                    icon.unbind('click').bind('click', click_image);
                    icon.show();
                }, function (eventObject) {
                    $(".hover-icon").hide();
                    $(".hover-icon:hover").show();
                } );

                $(icon).hover(
                    function(){
                        $(this).show();
                    },
                    function(){
                        $(this).hide();
                    });

            }

        function _updateImageArray(newArray) {
            if (!newArray.length){
                return;
            }
            if (!settings.haveShown) {
                settings.delayUntilShown.push(function(){
                    _updateImageArray(newArray);
                });
                return;
            }
            var currentId = settings.imageArray[settings.activeImage][5];
            settings.imageArray.length = 0;
            settings.activeImage = 0;
            for ( var i = 0; i < newArray.length; i++ ) {
                settings.imageArray.push(newArray[i]);
            }
            while ( settings.imageArray[settings.activeImage][5] != currentId ) {
                settings.activeImage++;
            }
            // Call the function that prepares image exhibition
            //$('#lightbox-image,#lightbox-container-image-data-box,#lightbox-image-details-currentNumber').hide();
            jQueryMatchedObj.data('imageArray', newArray);
            _set_image_to_view(false);
        }

        old_hover_icons = $(".hover-icon");
        old_hover_icons.remove();
        for ( var i = 0; i < this.length; i++ ) {
         addHoverToElement($($(this[i]).find("img")[0]));
        }
        this.unbind('click').click(_initialize);
        var lightBoxHooks = {
            updateImageArray: _updateImageArray
        };
        return lightBoxHooks;
    };
})(jQuery); // Call and execute the function immediately passing the jQuery object
