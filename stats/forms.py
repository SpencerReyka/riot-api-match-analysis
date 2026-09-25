from django import forms


class RiotIDForm(forms.Form):
    game_name = forms.CharField(
        label="Game name",
        max_length=32,
        widget=forms.TextInput(attrs={"placeholder": "Game name", "autocomplete": "off"}),
    )
    tag_line = forms.CharField(
        label="Tagline",
        max_length=8,
        widget=forms.TextInput(attrs={"placeholder": "NA1", "autocomplete": "off"}),
    )

    def clean_game_name(self) -> str:
        return self.cleaned_data["game_name"].strip()

    def clean_tag_line(self) -> str:
        return self.cleaned_data["tag_line"].strip().lstrip("#")


class PublicAnalysisRequestForm(RiotIDForm):
    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("The request could not be accepted.")
        return cleaned


class RiotAPIKeyForm(forms.Form):
    api_key = forms.CharField(
        label="New Riot API key",
        max_length=128,
        strip=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "RGAPI-…",
            },
            render_value=False,
        ),
        help_text="The existing key is never displayed. Saving replaces it immediately.",
    )

    def clean_api_key(self) -> str:
        api_key = self.cleaned_data["api_key"].strip()
        if not api_key.startswith("RGAPI-"):
            raise forms.ValidationError("Enter a Riot API key beginning with RGAPI-.")
        return api_key
