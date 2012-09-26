'''
This module is responsible for building the create / edit / delete account dialogs, which are created and controlled by
a non-trivial amount of hooks.

The default_ui module handles nearly everything for the 'standard' service providers / components and should be used
as the primary example for implementing future hook handlers used in this plugin.

Notes:
 * All hooks begin with 'digsby.services.edit.' unless otherwise specifed.
 * the 'parent' argument is passed to wx controls as their parent window and as such follows the rules of the wx library.
 * 'SP' indicates a concrete service provider instance
 * 'MSP' indicates meta information (usually a dictionary) about the service provider
 * 'info' is usually a mapping of information that will be used to create (or update) a concrete service component instance.
 * 'MSC' indicates meta information about the service component in question.

The categories of hooks are broken down in to 5 categories:
1. Dialog instantiation and saving.
    This is the main entry / exit point of this feature. A service provider can be created, edited, or deleted.
2. UI construction. The UI is broken down into two main panels: basic and advanced. the basic panel is always
    shown, while the advanced panel is hidden in a collapsable section. Additionally, for both panels, there are
    separate hooks for each component of the service provider, as well as the provider itself, to make changes to
    the panel.
3. UI Layout. In some cases it may be necessary to touch-up, or 'polish' the UI to look *just right*. For this,
    the 'layout.polish' hook is used.
3.5. Event binding. There are currently no hooks for event binding, but they may be needed in the future if
    the family of UI controls in these dialogs (specifically, the events they generate) gets larger.
4. Validation. When user input occurs, the data in the dialog is validated and feedback may be given to the user
    if appropriate.
5. Data extraction. In the same manner that the dialog was built, data needs to be extracted from it. This follows
    a similar pattern as #2.

Dialog instantiation and saving: (full hook names given in this section)
    digsby.services.create(parent, sp_info)
        invoked when creating a new service provider instance.
    digsby.services.edit(parent, sp)
        same as create, but instead of metainfo we have the service provider's details.
    digsby.services.edit.save(SP, MSP, info, callback = None)
        called when saving an edited account.
    digsby.services.delete.build_dialog(parent, SP)
        similar to edit, except the service provider will be deleted when finished.

UI Construction:
    {basic|advanced}.construct_panel(parent, SP, MSP)
        creates the specified panel and UI components and sizers that other hooks will add to.
    {basic|advanced}.construct_sub.{provider|im|email|social}(panel, SP, MSP, MSC)
        extension point for the provider or each type of component to add controls to the specified panel.

UI Layout:
    layout.polish(basic_panel, advanced_panel)
        here the panels may be modified however necessary to provide the desired appearance.

Validation: (full hook name given)
    digsby.services.validate(info, MSP, is_new)
        called on ui events that may require data to be verified. is_new specifies if the account is being created or edited.

Data extraction:
    {basic|advanced}.extract_panel(parent, SP, MSP)
    {basic|advanced}.extract_sub.{provider|im|email|social}(panel, SP, MSP, MSC)
        These hooks should retrieve data from UI components created in the analogous 'construct' hooks

Misc: (full hook names given)
  digsby.services.normalize(info, MSP, is_new)
      Used to modify any data before it's used to update / create anything.
  digsby.services.colorize_name(name)
      Used to split the name into 'tagged' components (i.e. name, base) for coloring in the UI.

'''
